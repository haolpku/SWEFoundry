#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEP_DIRS = {
    1: '1-parse-png-chunks',
    2: '2-verify-crc-and-chunk-invariants',
    3: '3-extract-deterministic-asset-metadata',
    4: '4-plan-deterministic-png-cleanup',
    5: '5-integrated-png-audit',
}
MUTANTS = {
    1: 'fp1_ignores_trailing_truncation.py',
    2: 'fp2_skips_ancillary_crc.py',
    3: 'fp3_input_order_text.py',
    4: 'fp4_repairs_critical_by_drop.py',
    5: 'fp5_metadata_only_audit.py',
}

def clean_env():
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env

def workspace():
    tmp = Path(tempfile.mkdtemp(prefix='tdf-png-audit-'))
    shutil.copytree(ROOT / 'environment' / 'codebase', tmp / 'environment' / 'codebase')
    return tmp

def apply_solution(ws, step):
    solve = ROOT / 'steps' / STEP_DIRS[step] / 'solution' / 'solve.sh'
    env = clean_env()
    env['TDF_WORKSPACE'] = str(ws)
    proc = subprocess.run(['/bin/sh', str(solve)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode == 0

def run_verifier(ws, step, extra_env=None):
    reward = ws / 'reward' / f'step-{step}'
    env = clean_env()
    if extra_env:
        env.update(extra_env)
    env['TDF_WORKSPACE'] = str(ws)
    env['TDF_TESTS_DIR'] = str(ROOT)
    env['TDF_REWARD_DIR'] = str(reward)
    ver = ROOT / 'steps' / STEP_DIRS[step] / 'tests' / 'verifier.py'
    proc = subprocess.run([sys.executable, str(ver)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    metrics_path = reward / 'reward.json'
    metrics = json.loads(metrics_path.read_text(encoding='utf-8')) if metrics_path.exists() else {'release_pass': -1}
    return {'returncode': proc.returncode, 'release_pass': metrics.get('release_pass'), 'correctness': metrics.get('correctness')}

def apply_mutant(ws, step):
    env = clean_env()
    env['TDF_WORKSPACE'] = str(ws)
    proc = subprocess.run([sys.executable, str(ROOT / 'verifier' / 'anti_cheat' / MUTANTS[step]), str(ws)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode == 0

def add_gate(gates, name, passed, observed=None):
    gate = {'name': name, 'passed': bool(passed)}
    if observed is not None:
        gate['observed'] = observed
    gates.append(gate)

def main():
    gates = []
    for step in range(1, 6):
        ws = workspace()
        try:
            result = run_verifier(ws, step)
            add_gate(gates, f'starter_step_{step}_release_pass_zero', result['release_pass'] == 0, result)
        finally:
            shutil.rmtree(ws, ignore_errors=True)
        ws = workspace()
        try:
            applied = all(apply_solution(ws, s) for s in range(1, step + 1))
            result = run_verifier(ws, step)
            add_gate(gates, f'oracle_cumulative_step_{step}_release_pass_one', applied and result['release_pass'] == 1, result)
        finally:
            shutil.rmtree(ws, ignore_errors=True)
    for step in range(1, 6):
        ws = workspace()
        try:
            applied = all(apply_solution(ws, s) for s in range(1, 6)) and apply_mutant(ws, step)
            result = run_verifier(ws, step)
            add_gate(gates, f'mutant_fp{step}_release_pass_zero', applied and result['release_pass'] == 0, result)
        finally:
            shutil.rmtree(ws, ignore_errors=True)
    ws = workspace()
    try:
        applied = all(apply_solution(ws, s) for s in range(1, 6))
        codebase = ws / 'environment' / 'codebase'
        (codebase / 'sitecustomize.py').write_text("from pathlib import Path\nPath('sitecustomize-executed').write_text('bad')\nraise SystemExit('sitecustomize loaded')\n", encoding='utf-8')
        poison = ws / 'poison'
        (poison / 'png_asset_pipeline').mkdir(parents=True)
        (poison / 'png_asset_pipeline' / '__init__.py').write_text("raise SystemExit('PYTHONPATH poison imported')\n", encoding='utf-8')
        result = run_verifier(ws, 1, {'PYTHONPATH': str(poison)})
        marker_absent = not (ws / 'sitecustomize-executed').exists()
        add_gate(gates, 'sitecustomize_and_pythonpath_isolation', applied and marker_absent and result['release_pass'] == 1, {'release_pass': result['release_pass'], 'sitecustomize_marker': 'absent' if marker_absent else 'present'})
    finally:
        shutil.rmtree(ws, ignore_errors=True)
    gates = sorted(gates, key=lambda g: g['name'])
    report = {'task_id': 'mini-png-asset-pipeline', 'gates': gates, 'passed': all(g['passed'] for g in gates)}
    out = ROOT / 'verifier' / 'audit-report.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
