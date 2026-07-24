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
STEPS = [{'id': 'step-1', 'dir': 'steps/1-canonicalize-requests-and-responses', 'mutant': 'verifier/anti_cheat/fp1_ignores_vary.py'}, {'id': 'step-2', 'dir': 'steps/2-evaluate-freshness-and-stale-policy', 'mutant': 'verifier/anti_cheat/fp2_expires_over_max_age.py'}, {'id': 'step-3', 'dir': 'steps/3-merge-conditional-304-responses', 'mutant': 'verifier/anti_cheat/fp3_drops_body_on_304.py'}, {'id': 'step-4', 'dir': 'steps/4-apply-invalidation-rules', 'mutant': 'verifier/anti_cheat/fp4_invalidates_only_exact_key.py'}, {'id': 'step-5', 'dir': 'steps/5-integrated-cache-audit-and-recovery', 'mutant': 'verifier/anti_cheat/fp5_replays_before_snapshot_validation.py'}]
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', 'audit-report.json', 'reward.txt', 'reward.json', 'evidence.json', 'ctrf.json', 'case_scripts', 'audit_rewards')

def copy_path(src: pathlib.Path, dst: pathlib.Path):
    if src.is_dir():
        shutil.copytree(src, dst, ignore=IGNORE)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def make_workspace(base: pathlib.Path) -> pathlib.Path:
    ws = base / 'workspace'
    for rel in ['environment/codebase', 'steps', 'verifier']:
        copy_path(ROOT / rel, ws / rel)
    return ws

def run_cmd(cmd, cwd: pathlib.Path, env: dict[str, str]):
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    return {'returncode': proc.returncode, 'stdout': proc.stdout[-1000:], 'stderr': proc.stderr[-1000:]}

def base_env(ws: pathlib.Path):
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['TDF_WORKSPACE'] = str(ws)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env

def apply_solution(ws: pathlib.Path, spec: dict[str, str]):
    env = base_env(ws)
    script = ws / spec['dir'] / 'solution' / 'solve.sh'
    return run_cmd([str(script)], ws, env)

def run_verifier(ws: pathlib.Path, spec: dict[str, str], label: str):
    reward_dir = ws / 'audit_rewards' / label
    reward_dir.mkdir(parents=True, exist_ok=True)
    env = base_env(ws)
    env['TDF_TESTS_DIR'] = str(ws / spec['dir'] / 'tests')
    env['TDF_REWARD_DIR'] = str(reward_dir)
    verifier = ws / spec['dir'] / 'tests' / 'verifier.py'
    proc = run_cmd([sys.executable, str(verifier)], ws, env)
    metrics_path = reward_dir / 'reward.json'
    metrics = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding='utf-8'))
    return {'returncode': proc['returncode'], 'release_pass': metrics.get('release_pass'), 'correctness': metrics.get('correctness')}

def run_mutant(ws: pathlib.Path, spec: dict[str, str]):
    env = base_env(ws)
    return run_cmd([sys.executable, str(ws / spec['mutant'])], ws, env)

def isolation_probe(base: pathlib.Path):
    bad = base / 'malicious_pythonpath'
    marker = base / 'sitecustomize_marker'
    bad.mkdir(parents=True, exist_ok=True)
    (bad / 'sitecustomize.py').write_text('import pathlib\npathlib.Path(' + repr(str(marker)) + ").write_text('loaded', encoding='utf-8')\nraise SystemExit(37)\n", encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONPATH'] = str(bad)
    env['PYTHONHOME'] = str(bad / 'fake-home')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    proc = subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.dont_write_bytecode=True; print(1)'], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    return {'gate': 'sitecustomize_and_pythonpath_isolation', 'passed': proc.returncode == 0 and proc.stdout.strip() == '1' and (not marker.exists())}

def main() -> int:
    gates = []
    mutants = []
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as tmpname:
        tmp = pathlib.Path(tmpname)
        gates.append(isolation_probe(tmp))
        for spec in STEPS:
            with tempfile.TemporaryDirectory(dir=tmp) as case_tmp:
                ws = make_workspace(pathlib.Path(case_tmp))
                observed = run_verifier(ws, spec, 'starter-' + spec['id'])
                gates.append({'gate': 'starter_' + spec['id'] + '_release_pass_zero', 'passed': observed['release_pass'] == 0, 'observed_release_pass': observed['release_pass']})
            with tempfile.TemporaryDirectory(dir=tmp) as case_tmp:
                ws = make_workspace(pathlib.Path(case_tmp))
                solved = apply_solution(ws, spec)
                observed = run_verifier(ws, spec, 'oracle-' + spec['id'])
                gates.append({'gate': 'oracle_' + spec['id'] + '_release_pass_one', 'passed': solved['returncode'] == 0 and observed['release_pass'] == 1, 'observed_release_pass': observed['release_pass']})
        complete = STEPS[-1]
        for spec in STEPS:
            with tempfile.TemporaryDirectory(dir=tmp) as case_tmp:
                ws = make_workspace(pathlib.Path(case_tmp))
                solved = apply_solution(ws, complete)
                mutation = run_mutant(ws, spec)
                observed = run_verifier(ws, spec, 'mutant-' + spec['id'])
                mutants.append({'mutant': pathlib.Path(spec['mutant']).stem, 'step': spec['id'], 'passed': solved['returncode'] == 0 and mutation['returncode'] == 0 and (observed['release_pass'] == 0), 'observed_release_pass': observed['release_pass']})
    gates = sorted(gates, key=lambda item: item['gate'])
    mutants = sorted(mutants, key=lambda item: item['mutant'])
    all_passed = all((item['passed'] for item in gates)) and all((item['passed'] for item in mutants))
    report = {'passed': all_passed, 'gates': gates, 'mutants': mutants}
    out = ROOT / 'verifier' / 'audit-report.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if all_passed else 1
if __name__ == '__main__':
    raise SystemExit(main())
