#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
STEP_SLUGS = {
    1: '1-read-wasm-binary-sections',
    2: '2-decode-type-import-and-export-metadata',
    3: '3-validate-structural-integrity',
    4: '4-report-compatibility-migrations',
    5: '5-integrated-wasm-audit',
}
MUTANTS = {
    1: 'fp1_accepts_truncated_section.py',
    2: 'fp2_single_index_space.py',
    3: 'fp3_custom_breaks_order.py',
    4: 'fp4_rewrites_input.py',
    5: 'fp5_summary_before_validation.py',
}

def copy_workspace(tmp: pathlib.Path) -> pathlib.Path:
    ws = tmp / 'workspace'
    dst = ws / 'environment' / 'codebase'
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'environment' / 'codebase', dst)
    return ws

def apply_solution(ws: pathlib.Path, step: int) -> None:
    src = ROOT / 'steps' / STEP_SLUGS[step] / 'solution' / 'files'
    dst = ws / 'environment' / 'codebase'
    for item in sorted(src.rglob('*')):
        if item.is_file():
            rel = item.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)

def apply_cumulative(ws: pathlib.Path, upto: int) -> None:
    for step in range(1, upto + 1):
        apply_solution(ws, step)

def run_step(ws: pathlib.Path, step: int, label: str, extra_env: dict[str, str] | None = None) -> dict:
    reward = ws / 'reward' / f'{label}-step-{step}'
    env = dict(os.environ)
    env['TDF_WORKSPACE'] = str(ws)
    env['TDF_REWARD_DIR'] = str(reward)
    env['TDF_TESTS_DIR'] = str(ROOT / 'steps' / STEP_SLUGS[step] / 'tests')
    env['TDF_VERIFIER_ROOT'] = str(ROOT)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run([str(ROOT / 'steps' / STEP_SLUGS[step] / 'tests' / 'test.sh')], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    reward_json = reward / 'reward.json'
    release = None
    correctness = None
    if reward_json.exists():
        data = json.loads(reward_json.read_text(encoding='utf-8'))
        release = data.get('release_pass')
        correctness = data.get('correctness')
    return {'returncode': proc.returncode, 'release_pass': release, 'correctness': correctness}

def starter_gate(step: int) -> dict:
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as td:
        ws = copy_workspace(pathlib.Path(td))
        if step > 1:
            apply_cumulative(ws, step - 1)
        return run_step(ws, step, 'starter')

def oracle_gate(step: int) -> dict:
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as td:
        ws = copy_workspace(pathlib.Path(td))
        apply_cumulative(ws, step)
        return run_step(ws, step, 'oracle')

def mutant_gate(step: int) -> dict:
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as td:
        ws = copy_workspace(pathlib.Path(td))
        apply_cumulative(ws, 5)
        env = dict(os.environ)
        env['TDF_WORKSPACE'] = str(ws)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        mut = subprocess.run([sys.executable, str(ROOT / 'verifier' / 'anti_cheat' / MUTANTS[step])], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result = run_step(ws, step, 'mutant')
        result['mutant_applied'] = mut.returncode == 0
        return result

def isolation_probe() -> dict:
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as td:
        base = pathlib.Path(td)
        ws = copy_workspace(base)
        apply_cumulative(ws, 5)
        trap = base / 'trap'
        trap.mkdir()
        marker = base / 'sitecustomize-loaded'
        (trap / 'sitecustomize.py').write_text("import pathlib\npathlib.Path(%r).write_text('loaded')\n" % str(marker), encoding='utf-8')
        pkg = trap / 'wasm_auditor'
        pkg.mkdir()
        (pkg / '__init__.py').write_text("raise RuntimeError('PYTHONPATH package imported')\n", encoding='utf-8')
        code = "import pathlib, sys\nsys.dont_write_bytecode=True\nsys.path.insert(0, %r)\nimport wasm_auditor\nassert wasm_auditor.parse_wasm_sections(b'\\x00asm\\x01\\x00\\x00\\x00') == []\nassert not pathlib.Path(%r).exists()\n" % (str(ws / 'environment' / 'codebase'), str(marker))
        env = dict(os.environ)
        env['PYTHONPATH'] = str(trap)
        env['PYTHONHOME'] = str(trap)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        proc = subprocess.run([sys.executable, '-I', '-c', code], cwd=str(ws), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return {'returncode': proc.returncode, 'release_pass': 1 if proc.returncode == 0 else 0, 'marker_created': marker.exists()}

def normalize(result: dict, expect_release: int) -> dict:
    return {'passed': result.get('release_pass') == expect_release and result.get('returncode') == (0 if expect_release == 1 else result.get('returncode')), 'release_pass': result.get('release_pass'), 'correctness': result.get('correctness')}

def main() -> int:
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['TDF_PYTHON'] = sys.executable
    gates = {}
    ok = True
    for step in range(1, 6):
        r = starter_gate(step)
        passed = r.get('release_pass') == 0
        gates[f'step_{step}_starter_release_pass_0'] = {'passed': passed, 'release_pass': r.get('release_pass'), 'correctness': r.get('correctness')}
        ok = ok and passed
        r = oracle_gate(step)
        passed = r.get('release_pass') == 1 and r.get('correctness') == 1.0
        gates[f'step_{step}_oracle_release_pass_1'] = {'passed': passed, 'release_pass': r.get('release_pass'), 'correctness': r.get('correctness')}
        ok = ok and passed
    for step in range(1, 6):
        r = mutant_gate(step)
        passed = r.get('mutant_applied') is True and r.get('release_pass') == 0
        gates[f'fp{step}_mutant_killed_by_step_{step}'] = {'passed': passed, 'release_pass': r.get('release_pass'), 'correctness': r.get('correctness'), 'mutant_applied': r.get('mutant_applied')}
        ok = ok and passed
    r = isolation_probe()
    passed = r.get('release_pass') == 1 and r.get('marker_created') is False
    gates['sitecustomize_and_pythonpath_isolation'] = {'passed': passed, 'release_pass': r.get('release_pass'), 'marker_created': r.get('marker_created')}
    ok = ok and passed
    report = {'gates': {k: gates[k] for k in sorted(gates)}, 'passed': ok, 'task_id': ROOT.name}
    out = ROOT / 'verifier' / 'audit-report.json'
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
