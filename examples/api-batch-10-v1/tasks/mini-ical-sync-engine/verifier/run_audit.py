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
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
STEPS = [(1, 'steps/1-parse-icalendar-components'), (2, 'steps/2-expand-bounded-recurrences'), (3, 'steps/3-apply-incremental-sync-changes'), (4, 'steps/4-resolve-sync-conflicts'), (5, 'steps/5-integrated-calendar-sync-recovery')]
MUTANTS = [(1, 'fp1_ignores_folding.py'), (2, 'fp2_until_exclusive_only.py'), (3, 'fp3_resurrects_deleted_event.py'), (4, 'fp4_input_order_winner.py'), (5, 'fp5_expands_before_conflict_resolution.py')]

def make_workspace(base: Path) -> Path:
    ws = base / 'workspace'
    (ws / 'environment').mkdir(parents=True)
    shutil.copytree(ROOT / 'environment' / 'codebase', ws / 'environment' / 'codebase')
    return ws

def run_cmd(argv: list[str], env: dict[str, str], cwd: Path=ROOT) -> subprocess.CompletedProcess:
    clean = dict(env)
    clean['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run(argv, cwd=str(cwd), env=clean, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def apply_solutions(ws: Path, through_step: int) -> bool:
    env = dict(os.environ)
    env['TDF_WORKSPACE'] = str(ws)
    for index, step_dir in STEPS[:through_step]:
        proc = run_cmd([str(ROOT / step_dir / 'solution' / 'solve.sh')], env)
        if proc.returncode != 0:
            return False
    return True

def run_step_verifier(step: int, ws: Path, extra_env: dict[str, str] | None=None) -> tuple[int | None, int]:
    step_dir = ROOT / STEPS[step - 1][1]
    reward = ws / ('reward-step-' + str(step))
    if reward.exists():
        shutil.rmtree(reward)
    env = dict(os.environ)
    env['TDF_WORKSPACE'] = str(ws)
    env['TDF_TESTS_DIR'] = str(step_dir / 'tests')
    env['TDF_REWARD_DIR'] = str(reward)
    if extra_env:
        env.update(extra_env)
    proc = run_cmd([str(step_dir / 'tests' / 'test.sh')], env)
    try:
        data = json.loads((reward / 'reward.json').read_text(encoding='utf-8'))
        return (int(data.get('release_pass')), proc.returncode)
    except Exception:
        return (None, proc.returncode)

def append_gate(gates: list[dict], gate: str, step: int, expected: int, observed: int | None, returncode: int, extra: str='') -> None:
    gates.append({'gate': gate, 'step': step, 'expected_release_pass': expected, 'observed_release_pass': observed, 'returncode_zero': returncode == 0, 'passed': observed == expected, 'extra': extra})

def main() -> int:
    gates: list[dict] = []
    with tempfile.TemporaryDirectory(prefix='mini-ical-audit-') as tmp_name:
        tmp = Path(tmp_name)
        for step, _ in STEPS:
            ws = make_workspace(tmp / ('starter-' + str(step)))
            observed, rc = run_step_verifier(step, ws)
            append_gate(gates, 'starter_release_pass_zero', step, 0, observed, rc)
        for step, _ in STEPS:
            ws = make_workspace(tmp / ('oracle-' + str(step)))
            ok = apply_solutions(ws, step)
            observed, rc = run_step_verifier(step, ws)
            append_gate(gates, 'oracle_release_pass_one', step, 1, observed if ok else None, rc, '' if ok else 'solution_apply_failed')
        for step, mutant in MUTANTS:
            ws = make_workspace(tmp / ('mutant-' + str(step)))
            ok = apply_solutions(ws, 5)
            env = dict(os.environ)
            env['TDF_WORKSPACE'] = str(ws)
            mproc = run_cmd([str(ROOT / 'verifier' / 'anti_cheat' / mutant)], env)
            observed, rc = run_step_verifier(step, ws)
            append_gate(gates, 'mutant_release_pass_zero', step, 0, observed if ok and mproc.returncode == 0 else None, rc, mutant)
        ws = make_workspace(tmp / 'isolation')
        ok = apply_solutions(ws, 1)
        hostile = tmp / 'hostile'
        (hostile / 'mini_ical_sync_engine').mkdir(parents=True)
        (hostile / 'sitecustomize.py').write_text("raise SystemExit('hostile sitecustomize loaded')\n", encoding='utf-8')
        (hostile / 'mini_ical_sync_engine' / '__init__.py').write_text("raise SystemExit('hostile package loaded')\n", encoding='utf-8')
        observed, rc = run_step_verifier(1, ws, {'PYTHONPATH': str(hostile), 'PYTHONHOME': str(tmp / 'bad-python-home')})
        append_gate(gates, 'sitecustomize_and_pythonpath_isolation', 1, 1, observed if ok else None, rc)
    report = {'passed': all((g['passed'] for g in gates)), 'gates': gates}
    report_path = ROOT / 'verifier' / 'audit-report.json'
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1
if __name__ == '__main__':
    raise SystemExit(main())
