#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TASK_ID = 'mini-posix-manifest-installer'
STEPS = {1: '1-validate-deployment-manifest', 2: '2-plan-atomic-install-operations', 3: '3-write-and-replay-intent-records', 4: '4-plan-rollback-from-manifest', 5: '5-integrated-safe-install-audit'}
MUTANTS = {1: 'fp1_allows_traversal.py', 2: 'fp2_mtime_comparison.py', 3: 'fp3_nonidempotent_replay.py', 4: 'fp4_trusts_backup_name.py', 5: 'fp5_plans_before_recovery.py'}

def clean_env(extra=None):
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra:
        env.update(extra)
    return env

def ignore(dirpath, names):
    return {n for n in names if n == '__pycache__' or n == 'reward' or n == 'audit-report.json' or n.endswith('.pyc')}

def make_workspace(parent):
    ws = Path(parent) / 'workspace'
    (ws / 'environment').mkdir(parents=True)
    shutil.copytree(ROOT / 'environment' / 'codebase', ws / 'environment' / 'codebase', ignore=ignore)
    shutil.copytree(ROOT / 'steps', ws / 'steps', ignore=ignore)
    shutil.copytree(ROOT / 'verifier', ws / 'verifier', ignore=ignore)
    return ws

def apply_solution(ws, step_num):
    solve = ws / 'steps' / STEPS[step_num] / 'solution' / 'solve.sh'
    proc = subprocess.run(['/bin/sh', str(solve)], cwd=str(ws), env=clean_env({'TDF_WORKSPACE': str(ws)}), text=True, capture_output=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError('solution application failed for step ' + str(step_num))

def apply_complete_oracle(ws):
    apply_solution(ws, 5)

def apply_mutant(ws, step_num):
    script = ws / 'verifier' / 'anti_cheat' / MUTANTS[step_num]
    proc = subprocess.run([sys.executable, str(script), str(ws)], cwd=str(ws), env=clean_env({'TDF_WORKSPACE': str(ws)}), text=True, capture_output=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError('mutant application failed for step ' + str(step_num))

def run_step_verifier(ws, step_num, label, extra_env=None):
    tests = ws / 'steps' / STEPS[step_num] / 'tests'
    reward = ws / 'audit_rewards' / label
    env_extra = {'TDF_WORKSPACE': str(ws), 'TDF_TESTS_DIR': str(tests), 'TDF_REWARD_DIR': str(reward)}
    if extra_env:
        env_extra.update(extra_env)
    proc = subprocess.run(['/bin/sh', str(tests / 'test.sh')], cwd=str(ws), env=clean_env(env_extra), text=True, capture_output=True, timeout=60)
    reward_file = reward / 'reward.json'
    if reward_file.exists():
        metrics = json.loads(reward_file.read_text(encoding='utf-8'))
        release = metrics.get('release_pass')
        correctness = metrics.get('correctness')
    else:
        release = None
        correctness = None
    return {'process_ok': proc.returncode == 0, 'release_pass': release, 'correctness': correctness}

def add_gate(gates, name, passed, observed=None):
    row = {'name': name, 'passed': bool(passed)}
    if observed is not None:
        row['observed'] = observed
    gates.append(row)

def main():
    gates = []
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as td:
        for step_num in sorted(STEPS):
            ws = make_workspace(Path(td) / ('starter_' + str(step_num)))
            result = run_step_verifier(ws, step_num, 'starter_step_' + str(step_num))
            add_gate(gates, 'starter_step_' + str(step_num) + '_release_pass_zero', result['process_ok'] and result['release_pass'] == 0, {'release_pass': result['release_pass'], 'correctness': result['correctness']})
        for step_num in sorted(STEPS):
            ws = make_workspace(Path(td) / ('oracle_' + str(step_num)))
            apply_solution(ws, step_num)
            result = run_step_verifier(ws, step_num, 'oracle_step_' + str(step_num))
            add_gate(gates, 'oracle_step_' + str(step_num) + '_release_pass_one', result['process_ok'] and result['release_pass'] == 1, {'release_pass': result['release_pass'], 'correctness': result['correctness']})
        for step_num in sorted(STEPS):
            ws = make_workspace(Path(td) / ('mutant_' + str(step_num)))
            apply_complete_oracle(ws)
            apply_mutant(ws, step_num)
            result = run_step_verifier(ws, step_num, 'mutant_step_' + str(step_num))
            add_gate(gates, 'mutant_step_' + str(step_num) + '_release_pass_zero', result['process_ok'] and result['release_pass'] == 0, {'release_pass': result['release_pass'], 'correctness': result['correctness']})
        ws = make_workspace(Path(td) / 'isolation')
        apply_complete_oracle(ws)
        poison = ws / 'poison'
        (poison / 'posix_manifest_installer').mkdir(parents=True)
        (poison / 'posix_manifest_installer' / '__init__.py').write_text('raise SystemExit(77)\n', encoding='utf-8')
        (ws / 'environment' / 'codebase' / 'sitecustomize.py').write_text("from pathlib import Path\nPath('sitecustomize-imported.txt').write_text('bad')\nraise SystemExit(88)\n", encoding='utf-8')
        result = run_step_verifier(ws, 1, 'isolation_probe', {'PYTHONPATH': str(poison), 'PYTHONHOME': str(poison / 'home')})
        marker_absent = not (ws / 'sitecustomize-imported.txt').exists()
        add_gate(gates, 'sitecustomize_and_pythonpath_isolation', result['process_ok'] and result['release_pass'] == 1 and marker_absent, {'release_pass': result['release_pass'], 'marker_absent': marker_absent})
    gates = sorted(gates, key=lambda g: g['name'])
    overall = all((g['passed'] for g in gates))
    report = {'schema_version': '1.0', 'task_id': TASK_ID, 'passed': overall, 'gates': gates}
    out = ROOT / 'verifier' / 'audit-report.json'
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if overall else 1
if __name__ == '__main__':
    raise SystemExit(main())
