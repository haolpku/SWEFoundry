from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Check:
    name: str
    func: Callable[[Path], Any]


def resolve_paths() -> tuple[Path, Path, Path]:
    workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()
    tests_dir = Path(os.environ.get('TDF_TESTS_DIR', Path.cwd())).resolve()
    reward_dir = Path(os.environ.get('TDF_REWARD_DIR', tests_dir)).resolve()
    reward_dir.mkdir(parents=True, exist_ok=True)
    return workspace, tests_dir, reward_dir


def _clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if extra:
        env.update({str(key): str(value) for key, value in extra.items()})
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def run_candidate(workspace: Path, body: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    codebase = workspace / 'environment' / 'codebase'
    bootstrap = 'import sys\nsys.dont_write_bytecode = True\nsys.path.insert(0, {!r})\n'.format(str(codebase))
    return subprocess.run([sys.executable, '-I', '-c', bootstrap + body], cwd=str(workspace), env=_clean_env(extra_env), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def run_json(workspace: Path, body: str, extra_env: dict[str, str] | None = None) -> Any:
    proc = run_candidate(workspace, body, extra_env)
    if proc.returncode != 0:
        raise AssertionError('candidate exited nonzero')
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError('candidate produced no JSON')
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise AssertionError('candidate produced invalid JSON') from exc


def expect_error(workspace: Path, body: str) -> bool:
    proc = run_candidate(workspace, body)
    if proc.returncode == 0:
        raise AssertionError('candidate accepted invalid input')
    return True


def run_step(step_id: str, checks: list[Check]) -> int:
    workspace, _tests_dir, reward_dir = resolve_paths()
    evidence_checks: list[dict[str, Any]] = []
    passed = 0
    for check in checks:
        ok = False
        message = ''
        try:
            check.func(workspace)
            ok = True
        except Exception as exc:  # deterministic evidence only
            message = exc.__class__.__name__
        if ok:
            passed += 1
        evidence_checks.append({'name': check.name, 'passed': ok, 'message': message})
    correctness = 1.0 if passed == len(checks) else passed / len(checks)
    release_pass = 1 if correctness == 1.0 else 0
    reward = {
        'correctness': correctness,
        'code_quality': correctness,
        'reasoning': correctness,
        'efficiency': correctness,
        'weighted_total': correctness,
        'release_pass': release_pass,
    }
    evidence = {'step_id': step_id, 'checks': evidence_checks, 'summary': {'passed': passed, 'total': len(checks)}}
    ctrf_tests = [{'name': item['name'], 'status': 'passed' if item['passed'] else 'failed'} for item in evidence_checks]
    ctrf = {'results': {'tool': {'name': 'tdf-blackbox-verifier'}, 'summary': {'tests': len(checks), 'passed': passed, 'failed': len(checks) - passed}, 'tests': ctrf_tests}}
    (reward_dir / 'reward.txt').write_text(str(correctness) + '\n', encoding='utf-8')
    with (reward_dir / 'reward.json').open('w', encoding='utf-8') as handle:
        json.dump(reward, handle, sort_keys=True)
        handle.write('\n')
    with (reward_dir / 'evidence.json').open('w', encoding='utf-8') as handle:
        json.dump(evidence, handle, sort_keys=True)
        handle.write('\n')
    with (reward_dir / 'ctrf.json').open('w', encoding='utf-8') as handle:
        json.dump(ctrf, handle, sort_keys=True)
        handle.write('\n')
    return 0 if release_pass else 1
