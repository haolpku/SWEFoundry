#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap

METRIC_KEYS = ['correctness', 'code_quality', 'reasoning', 'efficiency', 'weighted_total', 'release_pass']


def _clean_env():
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def _safe_name(name):
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', name)


def _case_source(case_name, body):
    indented = textwrap.indent(body.strip() + '\n', '    ')
    return f'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
os.environ.pop('PYTHONPATH', None)
os.environ.pop('PYTHONHOME', None)
CASE_NAME = {case_name!r}
NL = chr(10)
CODEBASE = Path(os.environ['TDF_WORKSPACE']) / 'environment' / 'codebase'
sys.path.insert(0, str(CODEBASE))
BASE = Path(os.environ['TDF_REWARD_DIR']) / 'case-data' / CASE_NAME
if BASE.exists():
    shutil.rmtree(BASE)
BASE.mkdir(parents=True)


def write_units(mapping):
    root = BASE / 'units'
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for rel, text in sorted(mapping.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    return root


def snapshot(path):
    base = Path(path)
    items = []
    for entry in sorted(p for p in base.rglob('*') if p.is_file()):
        items.append((entry.relative_to(base).as_posix(), entry.read_bytes().hex()))
    return items


def emit(ok, details=None):
    print(json.dumps({{'ok': bool(ok), 'details': details or {{}}}}, sort_keys=True))


def candidate_check():
{indented}

try:
    result = candidate_check()
    emit(True, result)
except AssertionError as exc:
    emit(False, {{'assertion': str(exc)}})
except BaseException as exc:
    emit(False, {{'exception_type': type(exc).__name__, 'message': str(exc)}})
'''


def run_candidate(case_name, body, workspace, reward_dir):
    scripts_dir = Path(reward_dir) / 'case-scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script = scripts_dir / (_safe_name(case_name) + '.py')
    script.write_text(_case_source(case_name, body), encoding='utf-8')
    env = _clean_env()
    env['TDF_WORKSPACE'] = str(Path(workspace))
    env['TDF_REWARD_DIR'] = str(Path(reward_dir))
    proc = subprocess.run([sys.executable, '-I', str(script)], cwd=str(workspace), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    parsed = None
    for line in reversed(proc.stdout.splitlines()):
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if parsed is None:
        parsed = {'ok': False, 'details': {'process_returncode': proc.returncode, 'no_json_protocol': True}}
    if proc.returncode != 0 and parsed.get('ok'):
        parsed = {'ok': False, 'details': {'process_returncode': proc.returncode}}
    return {'name': case_name, 'ok': bool(parsed.get('ok')), 'details': parsed.get('details') or {}}


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def run_verifier(step_id, checks):
    sys.dont_write_bytecode = True
    os.environ.pop('PYTHONPATH', None)
    os.environ.pop('PYTHONHOME', None)
    workspace = Path(os.environ['TDF_WORKSPACE']).resolve()
    tests_dir = Path(os.environ['TDF_TESTS_DIR']).resolve()
    reward_dir = Path(os.environ['TDF_REWARD_DIR']).resolve()
    reward_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, body in checks:
        results.append(run_candidate(name, body, workspace, reward_dir))
    passed = sum(1 for item in results if item['ok'])
    total = len(results)
    correctness = 1.0 if passed == total else round(passed / total, 6)
    release_pass = 1 if correctness == 1.0 else 0
    metrics = {
        'correctness': correctness,
        'code_quality': 1.0 if release_pass else 0.0,
        'reasoning': 1.0 if release_pass else 0.0,
        'efficiency': 1.0 if release_pass else 0.0,
        'weighted_total': correctness,
        'release_pass': release_pass,
    }
    assert list(metrics.keys()) == METRIC_KEYS
    evidence = {
        'checks': results,
        'step_id': step_id,
        'tests_dir_name': tests_dir.name,
        'workspace_contract': 'TDF_WORKSPACE/environment/codebase',
    }
    ctrf_tests = [{'name': item['name'], 'status': 'passed' if item['ok'] else 'failed'} for item in results]
    ctrf = {'results': {'summary': {'failed': total - passed, 'passed': passed, 'tests': total}, 'tests': ctrf_tests, 'tool': {'name': 'tdf-blackbox-verifier'}}}
    (reward_dir / 'reward.txt').write_text(str(metrics['weighted_total']) + '\n', encoding='utf-8')
    _write_json(reward_dir / 'reward.json', metrics)
    _write_json(reward_dir / 'evidence.json', evidence)
    _write_json(reward_dir / 'ctrf.json', ctrf)
    return 0 if release_pass else 1
