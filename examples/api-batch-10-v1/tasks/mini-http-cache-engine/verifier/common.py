#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys

METRIC_KEYS = ['correctness', 'code_quality', 'reasoning', 'efficiency', 'weighted_total', 'release_pass']


def resolve_paths(test_file: str):
    tests_dir = pathlib.Path(os.environ.get('TDF_TESTS_DIR', pathlib.Path(test_file).resolve().parent)).resolve()
    default_workspace = pathlib.Path(test_file).resolve().parents[3]
    workspace = pathlib.Path(os.environ.get('TDF_WORKSPACE', default_workspace)).resolve()
    reward_dir = pathlib.Path(os.environ.get('TDF_REWARD_DIR', tests_dir)).resolve()
    reward_dir.mkdir(parents=True, exist_ok=True)
    return workspace, tests_dir, reward_dir


def clean_env():
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def _safe_name(name: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in name)


def run_python_case(name: str, body: str, workspace: pathlib.Path, reward_dir: pathlib.Path):
    cases_dir = reward_dir / 'case_scripts'
    cases_dir.mkdir(parents=True, exist_ok=True)
    codebase = workspace / 'environment' / 'codebase'
    script = cases_dir / (_safe_name(name) + '.py')
    preamble = 'import json, sys\nsys.dont_write_bytecode = True\nsys.path.insert(0, ' + repr(str(codebase)) + ')\n'
    script.write_text(preamble + body, encoding='utf-8')
    proc = subprocess.run([sys.executable, '-I', str(script)], cwd=str(codebase), env=clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    stdout = proc.stdout.replace(str(workspace), '<workspace>')
    stderr = proc.stderr.replace(str(workspace), '<workspace>')
    parsed = {'ok': False, 'details': 'no json result'}
    if stdout.strip():
        lines = [line for line in stdout.splitlines() if line.strip()]
        try:
            parsed = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            parsed = {'ok': False, 'details': 'invalid json result: ' + exc.__class__.__name__}
    passed = proc.returncode == 0 and parsed.get('ok') is True
    return {'name': name, 'passed': passed, 'returncode': proc.returncode, 'details': parsed.get('details', {}), 'stdout': stdout[-1000:], 'stderr': stderr[-1000:]}


def finish(step_id: str, checks: list[tuple[str, str]], test_file: str) -> int:
    workspace, tests_dir, reward_dir = resolve_paths(test_file)
    del tests_dir
    results = [run_python_case(name, body, workspace, reward_dir) for name, body in checks]
    passed = sum(1 for item in results if item['passed'])
    total = len(results)
    correctness = 1.0 if passed == total else round(passed / total, 6)
    metrics = {key: 0.0 for key in METRIC_KEYS}
    metrics['correctness'] = correctness
    metrics['code_quality'] = 1.0 if correctness == 1.0 else 0.0
    metrics['reasoning'] = 1.0 if correctness == 1.0 else 0.0
    metrics['efficiency'] = 1.0 if correctness == 1.0 else 0.0
    metrics['weighted_total'] = correctness
    metrics['release_pass'] = 1 if correctness == 1.0 else 0
    evidence = {'step_id': step_id, 'checks': results, 'summary': {'passed': passed, 'total': total}}
    ctrf_tests = [{'name': item['name'], 'status': 'passed' if item['passed'] else 'failed', 'message': json.dumps(item['details'], sort_keys=True)} for item in results]
    ctrf = {'results': {'tool': {'name': 'mini-http-cache-engine-blackbox-verifier'}, 'summary': {'tests': total, 'passed': passed, 'failed': total - passed}, 'tests': ctrf_tests}}
    (reward_dir / 'reward.txt').write_text(str(metrics['weighted_total']) + '\n', encoding='utf-8')
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if metrics['release_pass'] == 1 else 1
