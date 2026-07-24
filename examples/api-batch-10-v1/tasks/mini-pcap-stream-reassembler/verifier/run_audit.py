#!/usr/bin/env python3
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
STEP_DIRS = [('step-1', '1-parse-classic-pcap-records'), ('step-2', '2-decode-ethernet-ipv4-tcp'), ('step-3', '3-reassemble-tcp-streams'), ('step-4', '4-emit-deterministic-timeout-events'), ('step-5', '5-integrated-pcap-audit-recovery')]
MUTANTS = [('step-1', 'fp1_native_endian_only.py'), ('step-2', 'fp2_ignores_ip_header_length.py'), ('step-3', 'fp3_append_arrival_order.py'), ('step-4', 'fp4_timeout_open_only_last.py'), ('step-5', 'fp5_drops_partial_flow_on_truncation.py')]

def base_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env

def make_workspace(tmp: Path) -> Path:
    ws = tmp / 'workspace'
    codebase_src = ROOT / 'environment' / 'codebase'
    codebase_dst = ws / 'environment' / 'codebase'
    codebase_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(codebase_src, codebase_dst, ignore=shutil.ignore_patterns('public_contract_tests', '__pycache__', '*.pyc'))
    return ws

def apply_solution(ws: Path, through_index: int) -> None:
    env = base_env()
    env['TDF_WORKSPACE'] = str(ws)
    for _, slug in STEP_DIRS[:through_index]:
        solve = ROOT / 'steps' / slug / 'solution' / 'solve.sh'
        subprocess.run([str(solve)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

def run_verifier(ws: Path, slug: str) -> dict:
    reward = ws / '.audit-reward' / slug
    tests = ws / '.audit-tests' / slug
    env = base_env()
    env['TDF_WORKSPACE'] = str(ws)
    env['TDF_REWARD_DIR'] = str(reward)
    env['TDF_TESTS_DIR'] = str(tests)
    env.pop('PYTHONPATH', None)
    proc = subprocess.run([str(ROOT / 'steps' / slug / 'tests' / 'test.sh')], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    reward_json = reward / 'reward.json'
    metrics = json.loads(reward_json.read_text(encoding='utf-8')) if reward_json.exists() else {'release_pass': None, 'correctness': 0.0}
    return {'returncode': proc.returncode, 'release_pass': metrics.get('release_pass'), 'correctness': metrics.get('correctness')}

def mutant_apply(ws: Path, mutant_name: str) -> None:
    env = base_env()
    env['TDF_WORKSPACE'] = str(ws)
    subprocess.run([str(ROOT / 'verifier' / 'anti_cheat' / mutant_name), str(ws)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

def isolation_probe() -> dict:
    with tempfile.TemporaryDirectory(prefix='tdf-isolation-') as td:
        tmp = Path(td)
        ws = make_workspace(tmp)
        apply_solution(ws, 5)
        poison = tmp / 'poison'
        poison.mkdir()
        marker = ws / 'sitecustomize-loaded.txt'
        (poison / 'sitecustomize.py').write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ").write_text('bad')\n", encoding='utf-8')
        probe = tmp / 'probe.py'
        probe.write_text('import pathlib, sys\nsys.dont_write_bytecode=True\nsys.path.insert(0, ' + repr(str(ws / 'environment' / 'codebase')) + ")\nimport pcap_reassembler\nprint('ok')\n", encoding='utf-8')
        env = base_env()
        env['PYTHONPATH'] = str(poison)
        proc = subprocess.run([sys.executable, '-I', '-B', str(probe)], cwd=str(ws), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return {'gate': 'sitecustomize_and_pythonpath_isolation', 'passed': proc.returncode == 0 and (not marker.exists())}

def main() -> int:
    gates = []
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as td:
        tmp_root = Path(td)
        for index, (step_id, slug) in enumerate(STEP_DIRS, 1):
            ws = make_workspace(tmp_root / ('starter-' + step_id))
            result = run_verifier(ws, slug)
            gates.append({'gate': 'starter_release_pass_zero', 'step': step_id, 'passed': result['release_pass'] == 0, 'observed_release_pass': result['release_pass']})
            ws = make_workspace(tmp_root / ('oracle-' + step_id))
            apply_solution(ws, index)
            result = run_verifier(ws, slug)
            gates.append({'gate': 'oracle_release_pass_one', 'step': step_id, 'passed': result['release_pass'] == 1, 'observed_release_pass': result['release_pass']})
        for step_id, mutant_name in MUTANTS:
            slug = dict(STEP_DIRS)[step_id]
            ws = make_workspace(tmp_root / ('mutant-' + step_id))
            apply_solution(ws, 5)
            mutant_apply(ws, mutant_name)
            result = run_verifier(ws, slug)
            gates.append({'gate': 'mutant_release_pass_zero', 'step': step_id, 'mutant': mutant_name, 'passed': result['release_pass'] == 0, 'observed_release_pass': result['release_pass']})
    gates.append(isolation_probe())
    gates = sorted(gates, key=lambda g: (g.get('gate', ''), g.get('step', ''), g.get('mutant', '')))
    report = {'task_id': 'mini-pcap-stream-reassembler', 'gates': gates, 'passed': all((g['passed'] for g in gates))}
    out = ROOT / 'verifier' / 'audit-report.json'
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + chr(10), encoding='utf-8')
    return 0 if report['passed'] else 1
if __name__ == '__main__':
    raise SystemExit(main())
