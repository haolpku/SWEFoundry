#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
ROOT = Path(__file__).resolve().parents[1]
ENV_CODEBASE = ROOT / 'environment' / 'codebase'
STEPS = [('step-1', ROOT / 'steps' / '1-parse-unit-files-deterministically'), ('step-2', ROOT / 'steps' / '2-validate-dependency-integrity'), ('step-3', ROOT / 'steps' / '3-compute-boot-activation-order'), ('step-4', ROOT / 'steps' / '4-replay-failure-recovery'), ('step-5', ROOT / 'steps' / '5-integrated-unit-audit')]
MUTANTS = [('step-1', ROOT / 'verifier' / 'anti_cheat' / 'fp1_last_key_wins.py'), ('step-2', ROOT / 'verifier' / 'anti_cheat' / 'fp2_requires_as_wants.py'), ('step-3', ROOT / 'verifier' / 'anti_cheat' / 'fp3_ignores_before.py'), ('step-4', ROOT / 'verifier' / 'anti_cheat' / 'fp4_wanted_failure_fatal.py'), ('step-5', ROOT / 'verifier' / 'anti_cheat' / 'fp5_drops_validation_on_cycle.py')]

def clean_env(extra=None):
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra:
        env.update(extra)
    return env

def make_workspace(base):
    workspace = Path(base) / 'workspace'
    (workspace / 'environment').mkdir(parents=True)
    shutil.copytree(ENV_CODEBASE, workspace / 'environment' / 'codebase')
    return workspace

def apply_solution(workspace, step_dir):
    solve = step_dir / 'solution' / 'solve.sh'
    env = clean_env({'TDF_WORKSPACE': str(workspace)})
    proc = subprocess.run([str(solve)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode == 0

def apply_complete_oracle(workspace):
    ok = True
    for _, step_dir in STEPS:
        ok = apply_solution(workspace, step_dir) and ok
    return ok

def run_step_verifier(workspace, step_id, step_dir, reward_name, extra_env=None):
    reward_dir = workspace / 'reward' / reward_name
    tests_dir = step_dir / 'tests'
    env_extra = {'TDF_WORKSPACE': str(workspace), 'TDF_TESTS_DIR': str(tests_dir), 'TDF_REWARD_DIR': str(reward_dir)}
    if extra_env:
        env_extra.update(extra_env)
    proc = subprocess.run([str(tests_dir / 'test.sh')], cwd=str(ROOT), env=clean_env(env_extra), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    reward_json = reward_dir / 'reward.json'
    release_pass = None
    correctness = None
    if reward_json.exists():
        data = json.loads(reward_json.read_text(encoding='utf-8'))
        release_pass = data.get('release_pass')
        correctness = data.get('correctness')
    return {'returncode': proc.returncode, 'release_pass': release_pass, 'correctness': correctness}

def apply_mutant(workspace, mutant):
    env = clean_env({'TDF_WORKSPACE': str(workspace)})
    proc = subprocess.run([sys.executable, str(mutant)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode == 0

def event(gate, step, observed, expected_release_pass):
    return {'expected_release_pass': expected_release_pass, 'gate': gate, 'passed': observed.get('release_pass') == expected_release_pass, 'release_pass': observed.get('release_pass'), 'returncode_zero': observed.get('returncode') == 0, 'step': step}

def main():
    report_events = []
    with tempfile.TemporaryDirectory(prefix='unit-linter-audit-') as tmp:
        base = Path(tmp)
        for step_id, step_dir in STEPS:
            workspace = make_workspace(base / ('starter-' + step_id))
            observed = run_step_verifier(workspace, step_id, step_dir, 'starter')
            report_events.append(event('starter_release_pass_is_zero', step_id, observed, 0))
        for index, (step_id, step_dir) in enumerate(STEPS):
            workspace = make_workspace(base / ('oracle-' + step_id))
            applied = True
            for _, cumulative_dir in STEPS[:index + 1]:
                applied = apply_solution(workspace, cumulative_dir) and applied
            observed = run_step_verifier(workspace, step_id, step_dir, 'oracle')
            item = event('cumulative_oracle_release_pass_is_one', step_id, observed, 1)
            item['solutions_applied'] = applied
            item['passed'] = item['passed'] and applied
            report_events.append(item)
        for step_id, mutant in MUTANTS:
            step_dir = dict(STEPS)[step_id]
            workspace = make_workspace(base / ('mutant-' + step_id))
            oracle_ok = apply_complete_oracle(workspace)
            mutant_ok = apply_mutant(workspace, mutant)
            observed = run_step_verifier(workspace, step_id, step_dir, 'mutant')
            item = event('complete_oracle_mutant_release_pass_is_zero', step_id, observed, 0)
            item['mutant'] = mutant.name
            item['oracle_applied'] = oracle_ok
            item['mutant_applied'] = mutant_ok
            item['passed'] = item['passed'] and oracle_ok and mutant_ok
            report_events.append(item)
        poison = base / 'poison'
        poison.mkdir()
        (poison / 'sitecustomize.py').write_text('raise SystemExit(99)\n', encoding='utf-8')
        poisoned_pkg = poison / 'mini_systemd_unit_linter'
        poisoned_pkg.mkdir()
        (poisoned_pkg / '__init__.py').write_text('raise SystemExit(98)\n', encoding='utf-8')
        workspace = make_workspace(base / 'isolation')
        oracle_ok = apply_complete_oracle(workspace)
        observed = run_step_verifier(workspace, 'step-5', dict(STEPS)['step-5'], 'isolation', {'PYTHONPATH': str(poison), 'PYTHONHOME': str(poison)})
        item = event('sitecustomize_and_pythonpath_isolation', 'step-5', observed, 1)
        item['oracle_applied'] = oracle_ok
        item['passed'] = item['passed'] and oracle_ok
        report_events.append(item)
    stable_events = sorted(report_events, key=lambda item: (item['gate'], item['step'], item.get('mutant', '')))
    passed = all((item['passed'] for item in stable_events))
    report = {'events': stable_events, 'passed': passed, 'summary': {'failed_gates': sum((1 for item in stable_events if not item['passed'])), 'total_gates': len(stable_events)}}
    report_path = ROOT / 'verifier' / 'audit-report.json'
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if passed else 1
if __name__ == '__main__':
    raise SystemExit(main())
