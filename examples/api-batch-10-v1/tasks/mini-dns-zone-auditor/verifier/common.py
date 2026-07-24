#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

METRIC_KEYS = ('correctness', 'code_quality', 'reasoning', 'efficiency', 'weighted_total', 'release_pass')

def get_context(default_step):
    workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()
    tests_dir = Path(os.environ.get('TDF_TESTS_DIR', Path.cwd())).resolve()
    reward_dir = Path(os.environ.get('TDF_REWARD_DIR', workspace / 'rewards' / default_step)).resolve()
    return workspace, tests_dir, reward_dir

def clean_env(extra=None):
    env = {}
    for key in ('HOME', 'PATH', 'SYSTEMROOT', 'WINDIR', 'LANG', 'LC_ALL', 'TMPDIR', 'TEMP', 'TMP'):
        if key in os.environ:
            env[key] = os.environ[key]
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONNOUSERSITE'] = '1'
    if extra:
        env.update(extra)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    return env

def _prelude(workspace):
    codebase = str(Path(workspace) / 'environment' / 'codebase')
    return '\n'.join([
        'import os, sys',
        'sys.dont_write_bytecode = True',
        "assert 'PYTHONPATH' not in os.environ, 'PYTHONPATH leaked into isolated case'",
        "assert 'PYTHONHOME' not in os.environ, 'PYTHONHOME leaked into isolated case'",
        'sys.path.insert(0, ' + repr(codebase) + ')',
    ]) + '\n'

def scrub(text, workspace):
    if text is None:
        return ''
    return str(text).replace(str(Path(workspace)), '<workspace>')

def run_case(name, body, workspace, timeout=8):
    code = _prelude(workspace) + body
    try:
        proc = subprocess.run([sys.executable, '-I', '-c', code], cwd=str(workspace), env=clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {'name': name, 'passed': proc.returncode == 0, 'returncode': proc.returncode, 'stdout': scrub(proc.stdout, workspace), 'stderr': scrub(proc.stderr, workspace)}
    except subprocess.TimeoutExpired as exc:
        return {'name': name, 'passed': False, 'returncode': 124, 'stdout': scrub(exc.stdout, workspace), 'stderr': '<timeout>'}

def finalize(step_id, checks, reward_dir):
    reward_dir.mkdir(parents=True, exist_ok=True)
    total = len(checks)
    passed = sum(1 for c in checks if c.get('passed'))
    correctness = 1.0 if total and passed == total else round(passed / total, 6) if total else 0.0
    release = 1 if correctness == 1.0 else 0
    metrics = {
        'correctness': correctness,
        'code_quality': correctness,
        'reasoning': correctness,
        'efficiency': correctness,
        'weighted_total': correctness,
        'release_pass': release,
    }
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, sort_keys=False, indent=2) + '\n', encoding='utf-8')
    (reward_dir / 'reward.txt').write_text('\n'.join(f'{k}={metrics[k]}' for k in METRIC_KEYS) + '\n', encoding='utf-8')
    evidence = {'step_id': step_id, 'metrics': metrics, 'checks': checks}
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    ctrf = {
        'results': {
            'tool': {'name': 'mini-dns-zone-auditor-blackbox-verifier'},
            'summary': {'tests': total, 'passed': passed, 'failed': total - passed},
            'tests': [{'name': c['name'], 'status': 'passed' if c.get('passed') else 'failed', 'message': c.get('stderr', '')[-400:]} for c in checks],
        }
    }
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return release
