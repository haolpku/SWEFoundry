import json
import os
import subprocess
import sys
from pathlib import Path

METRIC_KEYS = ['correctness', 'code_quality', 'reasoning', 'efficiency', 'weighted_total', 'release_pass']


def resolve_context(verifier_file):
    workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()
    tests_dir = Path(os.environ.get('TDF_TESTS_DIR', Path(verifier_file).resolve().parent)).resolve()
    reward_dir = Path(os.environ.get('TDF_REWARD_DIR', tests_dir / 'reward')).resolve()
    reward_dir.mkdir(parents=True, exist_ok=True)
    return workspace, tests_dir, reward_dir


def clean_env(extra=None):
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra:
        env.update(extra)
    return env


def _safe_name(name):
    return ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in name)


def run_case(step_id, name, code, workspace, reward_dir):
    case_dir = reward_dir / 'case_scripts'
    case_dir.mkdir(parents=True, exist_ok=True)
    script = case_dir / (_safe_name(name) + '.py')
    preamble = "import os\nimport sys\nsys.dont_write_bytecode = True\nsys.path.insert(0, os.environ['TDF_CODEBASE'])\n"
    script.write_text(preamble + code + '\n', encoding='utf-8')
    env = clean_env({'TDF_CODEBASE': str(workspace / 'environment' / 'codebase')})
    try:
        proc = subprocess.run([sys.executable, '-I', str(script)], cwd=str(workspace), env=env, text=True, capture_output=True, timeout=30)
        passed = proc.returncode == 0
        detail = {'returncode': proc.returncode}
        if not passed:
            detail['stdout_tail'] = proc.stdout[-1200:]
            detail['stderr_tail'] = proc.stderr[-1200:]
    except subprocess.TimeoutExpired as exc:
        passed = False
        detail = {'returncode': 'timeout', 'stdout_tail': (exc.stdout or '')[-1200:], 'stderr_tail': (exc.stderr or '')[-1200:]}
    return {'name': name, 'passed': bool(passed), 'detail': detail}


def run_cases(step_id, cases, workspace, reward_dir):
    return [run_case(step_id, name, code, workspace, reward_dir) for name, code in cases]


def write_outputs(step_id, checks, reward_dir):
    total = len(checks)
    passed = sum(1 for c in checks if c['passed'])
    correctness = 0.0 if total == 0 else passed / total
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
    reward_dir.mkdir(parents=True, exist_ok=True)
    (reward_dir / 'reward.txt').write_text(str(metrics['weighted_total']) + '\n', encoding='utf-8')
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    evidence = {'step_id': step_id, 'checks': checks, 'passed': passed, 'total': total}
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    ctrf = {'results': {'tool': {'name': 'tdf-black-box-verifier'}, 'summary': {'tests': total, 'passed': passed, 'failed': total - passed}, 'tests': [{'name': c['name'], 'status': 'passed' if c['passed'] else 'failed'} for c in checks]}}
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return metrics
