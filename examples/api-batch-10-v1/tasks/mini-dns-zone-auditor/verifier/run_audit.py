#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STEPS = [('step-1', 'steps/1-parse-zone-master-files', 'verifier/anti_cheat/fp1_case_sensitive_names.py'), ('step-2', 'steps/2-validate-zone-integrity', 'verifier/anti_cheat/fp2_allows_cname_mixed.py'), ('step-3', 'steps/3-simulate-offline-dns-answers', 'verifier/anti_cheat/fp3_unbounded_cname.py'), ('step-4', 'steps/4-plan-serial-and-digest-migration', 'verifier/anti_cheat/fp4_digest_input_order.py'), ('step-5', 'steps/5-integrated-zone-audit', 'verifier/anti_cheat/fp5_skips_queries_on_problems.py')]

def stable_env(extra=None):
    env = {}
    for key in ('HOME', 'PATH', 'SYSTEMROOT', 'WINDIR', 'LANG', 'LC_ALL', 'TMPDIR', 'TEMP', 'TMP'):
        if key in os.environ:
            env[key] = os.environ[key]
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONNOUSERSITE'] = '1'
    if extra:
        env.update(extra)
    return env

def copy_codebase(workspace):
    dst_env = workspace / 'environment'
    dst_env.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'environment' / 'codebase', dst_env / 'codebase', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

def run_cmd(cmd, env=None):
    return subprocess.run(cmd, cwd=str(ROOT), env=env or stable_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def apply_solution(workspace, index):
    solve = ROOT / STEPS[index][1] / 'solution' / 'solve.sh'
    env = stable_env({'TDF_WORKSPACE': str(workspace)})
    proc = run_cmd([str(solve)], env=env)
    return proc.returncode == 0

def make_workspace(tmpdir):
    workspace = Path(tmpdir) / 'workspace'
    copy_codebase(workspace)
    return workspace

def run_step(workspace, index, label, extra_env=None):
    step_id, step_dir, _ = STEPS[index]
    reward = workspace / 'audit_rewards' / label
    env_extra = {'TDF_WORKSPACE': str(workspace), 'TDF_TESTS_DIR': str(ROOT / step_dir / 'tests'), 'TDF_REWARD_DIR': str(reward)}
    if extra_env:
        env_extra.update(extra_env)
    proc = run_cmd([str(ROOT / step_dir / 'tests' / 'test.sh')], env=stable_env(env_extra))
    reward_json = reward / 'reward.json'
    release = -1
    if reward_json.exists():
        try:
            release = int(json.loads(reward_json.read_text(encoding='utf-8')).get('release_pass', -1))
        except Exception:
            release = -1
    return {'returncode': proc.returncode, 'release_pass': release}

def complete_oracle(workspace):
    for i in range(len(STEPS)):
        if not apply_solution(workspace, i):
            return False
    return True

def add_gate(gates, name, ok, detail=''):
    gates.append({'name': name, 'passed': bool(ok), 'detail': detail if detail else 'ok' if ok else 'failed'})

def cumulative_gates(gates):
    for i, (step_id, _, _) in enumerate(STEPS):
        with tempfile.TemporaryDirectory(prefix='tdf-audit-') as tmp:
            workspace = make_workspace(tmp)
            prior_ok = True
            for j in range(i):
                prior_ok = apply_solution(workspace, j) and prior_ok
            starter = run_step(workspace, i, 'starter-' + step_id)
            add_gate(gates, 'starter_' + step_id + '_release_pass_is_0', prior_ok and starter['release_pass'] == 0, 'release_pass=' + str(starter['release_pass']))
            solved = apply_solution(workspace, i)
            oracle = run_step(workspace, i, 'oracle-' + step_id)
            add_gate(gates, 'oracle_' + step_id + '_release_pass_is_1', solved and oracle['release_pass'] == 1, 'release_pass=' + str(oracle['release_pass']))

def mutant_gates(gates):
    for i, (step_id, _, mutant) in enumerate(STEPS):
        with tempfile.TemporaryDirectory(prefix='tdf-audit-') as tmp:
            workspace = make_workspace(tmp)
            ok = complete_oracle(workspace)
            proc = run_cmd([sys.executable, str(ROOT / mutant)], env=stable_env({'TDF_WORKSPACE': str(workspace)}))
            result = run_step(workspace, i, 'mutant-' + step_id)
            add_gate(gates, 'mutant_' + step_id + '_release_pass_is_0', ok and proc.returncode == 0 and (result['release_pass'] == 0), 'release_pass=' + str(result['release_pass']))

def isolation_gates(gates):
    with tempfile.TemporaryDirectory(prefix='tdf-audit-') as tmp:
        workspace = make_workspace(tmp)
        ok = complete_oracle(workspace)
        poison = Path(tmp) / 'poison'
        poison.mkdir()
        (poison / 'sitecustomize.py').write_text('raise SystemExit("poison sitecustomize loaded")\n', encoding='utf-8')
        (poison / 'dns_zone_auditor.py').write_text('raise SystemExit("poison module loaded")\n', encoding='utf-8')
        script = 'import sys; sys.dont_write_bytecode=True; sys.path.insert(0, ' + repr(str(workspace / 'environment' / 'codebase')) + '); import dns_zone_auditor; assert hasattr(dns_zone_auditor, "parse_zone")'
        proc = run_cmd([sys.executable, '-I', '-c', script], env=stable_env({'PYTHONPATH': str(poison)}))
        add_gate(gates, 'python_I_ignores_sitecustomize_and_pythonpath', ok and proc.returncode == 0)
        result = run_step(workspace, 0, 'isolation-step-1', extra_env={'PYTHONPATH': str(poison), 'PYTHONHOME': str(poison)})
        add_gate(gates, 'verifier_strips_pythonpath_and_pythonhome', ok and result['release_pass'] == 1, 'release_pass=' + str(result['release_pass']))

def main():
    gates = []
    cumulative_gates(gates)
    mutant_gates(gates)
    isolation_gates(gates)
    gates = sorted(gates, key=lambda g: g['name'])
    report = {'passed': all((g['passed'] for g in gates)), 'gates': gates, 'schema_version': '1.0', 'task_id': 'mini-dns-zone-auditor'}
    out = ROOT / 'verifier' / 'audit-report.json'
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1
if __name__ == '__main__':
    raise SystemExit(main())
