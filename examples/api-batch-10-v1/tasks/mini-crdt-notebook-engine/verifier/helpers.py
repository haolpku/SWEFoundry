from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap
from typing import Callable, Iterable

METRIC_KEYS = ['correctness', 'code_quality', 'reasoning', 'efficiency', 'weighted_total', 'release_pass']


def workspace_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get('TDF_WORKSPACE', pathlib.Path.cwd())).resolve()


def reward_path() -> pathlib.Path:
    default = workspace_path() / 'reward'
    return pathlib.Path(os.environ.get('TDF_REWARD_DIR', default)).resolve()


def clean_candidate_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra:
        env.update(extra)
        env.pop('PYTHONPATH', None)
        env.pop('PYTHONHOME', None)
    return env


def candidate_json(workspace: pathlib.Path, body: str) -> object:
    codebase = workspace / 'environment' / 'codebase'
    prelude = f'''
import json
import pathlib
import sys
sys.dont_write_bytecode = True
codebase = pathlib.Path({str(codebase)!r})
sys.path.insert(0, str(codebase))
'''
    code = textwrap.dedent(prelude) + '\n' + textwrap.dedent(body)
    proc = subprocess.run(
        [sys.executable, '-I', '-c', code],
        cwd=str(workspace),
        env=clean_candidate_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    if proc.returncode != 0:
        raise AssertionError('candidate exited nonzero: ' + proc.stderr.strip()[:500])
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError('candidate produced no JSON output')
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise AssertionError('candidate output was not JSON: ' + lines[-1][:500]) from exc


def assert_equal(actual: object, expected: object, message: str = '') -> None:
    if actual != expected:
        detail = message or f'expected {expected!r}, got {actual!r}'
        raise AssertionError(detail)


def assert_true(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def run_step(step_id: str, checks: Iterable[tuple[str, Callable[[pathlib.Path], None]]]) -> int:
    ws = workspace_path()
    results = []
    for name, func in checks:
        try:
            func(ws)
        except Exception as exc:  # noqa: BLE001 - verifier must report all black-box failures.
            results.append({'name': name, 'passed': False, 'message': f'{exc.__class__.__name__}: {str(exc)[:500]}'})
        else:
            results.append({'name': name, 'passed': True, 'message': ''})
    total = len(results)
    passed = sum(1 for item in results if item['passed'])
    correctness = 1.0 if total and passed == total else (passed / total if total else 0.0)
    release_pass = 1 if correctness == 1.0 else 0
    metrics = {
        'correctness': correctness,
        'code_quality': 1.0 if release_pass else correctness,
        'reasoning': 1.0 if release_pass else correctness,
        'efficiency': 1.0 if release_pass else correctness,
        'weighted_total': correctness,
        'release_pass': release_pass,
    }
    reward_dir = reward_path()
    reward_dir.mkdir(parents=True, exist_ok=True)
    (reward_dir / 'reward.txt').write_text(f'{metrics["weighted_total"]}\n', encoding='utf-8')
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    evidence = {'step_id': step_id, 'metrics': metrics, 'checks': results}
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    ctrf_tests = [
        {'name': item['name'], 'status': 'passed' if item['passed'] else 'failed', 'message': item['message']}
        for item in results
    ]
    ctrf = {
        'results': {
            'tool': {'name': 'mini-crdt-notebook-engine-blackbox-verifier'},
            'summary': {'tests': total, 'passed': passed, 'failed': total - passed},
            'tests': ctrf_tests,
        }
    }
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if release_pass else 1
