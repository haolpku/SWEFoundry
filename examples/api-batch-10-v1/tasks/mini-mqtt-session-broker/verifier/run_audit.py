#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

THIS = Path(__file__).resolve().parent
ROOT = THIS.parent
sys.path.insert(0, str(THIS))
from common import run_json

STEPS = [
    ('step-1', ROOT / 'steps' / '1-parse-broker-events'),
    ('step-2', ROOT / 'steps' / '2-match-wildcard-subscriptions'),
    ('step-3', ROOT / 'steps' / '3-replay-qos-and-retained-state'),
    ('step-4', ROOT / 'steps' / '4-plan-session-migration'),
    ('step-5', ROOT / 'steps' / '5-integrated-broker-replay-recovery'),
]
MUTANTS = [
    ('fp1_input_order_events', THIS / 'anti_cheat' / 'fp1_input_order_events.py', 0),
    ('fp2_hash_matches_partial_level', THIS / 'anti_cheat' / 'fp2_hash_matches_partial_level.py', 1),
    ('fp3_qos1_as_qos0', THIS / 'anti_cheat' / 'fp3_qos1_as_qos0.py', 2),
    ('fp4_uses_live_expiry', THIS / 'anti_cheat' / 'fp4_uses_live_expiry.py', 3),
    ('fp5_drops_retained_after_recovery', THIS / 'anti_cheat' / 'fp5_drops_retained_after_recovery.py', 4),
]


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def make_workspace(base: Path) -> Path:
    workspace = base / 'workspace'
    shutil.copytree(ROOT / 'environment' / 'codebase', workspace / 'environment' / 'codebase')
    return workspace


def apply_solution(workspace: Path, index: int) -> None:
    solve = STEPS[index][1] / 'solution' / 'solve.sh'
    proc = subprocess.run(['sh', str(solve)], cwd=str(ROOT), env=clean_env({'TDF_WORKSPACE': str(workspace)}), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise RuntimeError('solution application failed')


def complete_oracle(workspace: Path) -> None:
    for index in range(len(STEPS)):
        apply_solution(workspace, index)


def run_verifier(workspace: Path, index: int, label: str, extra_env: dict[str, str] | None = None) -> tuple[int, int]:
    step_id, step_dir = STEPS[index]
    reward_dir = workspace / 'audit_rewards' / label
    reward_dir.mkdir(parents=True, exist_ok=True)
    env = {'TDF_WORKSPACE': str(workspace), 'TDF_TESTS_DIR': str(step_dir / 'tests'), 'TDF_REWARD_DIR': str(reward_dir), 'PYTHONDONTWRITEBYTECODE': '1'}
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run([sys.executable, str(step_dir / 'tests' / 'verifier.py')], cwd=str(ROOT), env=clean_env(env), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    reward_path = reward_dir / 'reward.json'
    if not reward_path.exists():
        return proc.returncode, -1
    with reward_path.open('r', encoding='utf-8') as handle:
        reward = json.load(handle)
    return proc.returncode, int(reward.get('release_pass', -1))


def add_gate(gates: list[dict[str, object]], name: str, passed: bool, release_pass: int | None = None) -> None:
    item: dict[str, object] = {'name': name, 'passed': bool(passed)}
    if release_pass is not None:
        item['release_pass'] = release_pass
    gates.append(item)


def cumulative_gates(gates: list[dict[str, object]], tmp: Path) -> None:
    for index, (step_id, _step_dir) in enumerate(STEPS):
        before_root = tmp / ('before_' + step_id)
        before_root.mkdir()
        before_ws = make_workspace(before_root)
        for prior in range(index):
            apply_solution(before_ws, prior)
        rc, release = run_verifier(before_ws, index, 'starter_' + step_id)
        add_gate(gates, step_id + '_starter_release_pass_is_0', release == 0 and rc != 0, release)

        after_root = tmp / ('after_' + step_id)
        after_root.mkdir()
        after_ws = make_workspace(after_root)
        for current in range(index + 1):
            apply_solution(after_ws, current)
        rc, release = run_verifier(after_ws, index, 'oracle_' + step_id)
        add_gate(gates, step_id + '_oracle_release_pass_is_1', release == 1 and rc == 0, release)


def mutant_gates(gates: list[dict[str, object]], tmp: Path) -> None:
    for mutant_name, mutant_script, step_index in MUTANTS:
        root = tmp / ('mutant_' + mutant_name)
        root.mkdir()
        workspace = make_workspace(root)
        complete_oracle(workspace)
        proc = subprocess.run([sys.executable, str(mutant_script), str(workspace)], cwd=str(ROOT), env=clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        applied = proc.returncode == 0
        rc, release = run_verifier(workspace, step_index, mutant_name) if applied else (-1, -1)
        add_gate(gates, mutant_name + '_release_pass_is_0', applied and release == 0 and rc != 0, release)


def isolation_gate(gates: list[dict[str, object]], tmp: Path) -> None:
    root = tmp / 'isolation'
    root.mkdir()
    workspace = make_workspace(root)
    complete_oracle(workspace)
    poison = tmp / 'poison'
    (poison / 'mqtt_session_broker').mkdir(parents=True)
    (poison / 'sitecustomize.py').write_text('raise SystemExit(77)\n', encoding='utf-8')
    (poison / 'mqtt_session_broker' / '__init__.py').write_text('raise SystemExit(78)\n', encoding='utf-8')
    try:
        data = run_json(workspace, '''
import json
import mqtt_session_broker
print(json.dumps({'imported': mqtt_session_broker.__name__}))
''', {'PYTHONPATH': str(poison), 'PYTHONHOME': str(poison)})
        add_gate(gates, 'sitecustomize_and_pythonpath_isolation', data == {'imported': 'mqtt_session_broker'}, 1 if data == {'imported': 'mqtt_session_broker'} else 0)
    except Exception:
        add_gate(gates, 'sitecustomize_and_pythonpath_isolation', False, 0)


def main() -> int:
    gates: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix='mqtt-session-broker-audit-') as td:
        tmp = Path(td)
        cumulative_gates(gates, tmp)
        mutant_gates(gates, tmp)
        isolation_gate(gates, tmp)
    gates = sorted(gates, key=lambda item: str(item['name']))
    report = {'task_id': 'mini-mqtt-session-broker', 'gates': gates, 'passed': all(bool(item['passed']) for item in gates)}
    report_path = THIS / 'audit-report.json'
    with report_path.open('w', encoding='utf-8') as handle:
        json.dump(report, handle, sort_keys=True, indent=2)
        handle.write('\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
