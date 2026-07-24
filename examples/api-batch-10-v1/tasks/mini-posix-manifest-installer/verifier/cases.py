def step1_cases():
    return [
        ('valid_two_file_manifest_sorted_and_normalized', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); (base / 'src').mkdir()
    (base / 'src' / 'a').write_bytes(b'a'); (base / 'src' / 'b').write_bytes(b'b')
    m = base / 'm.json'
    json.dump({'files': [{'source': 'src/b', 'destination': 'z/../b.txt', 'sha256': h(b'b')}, {'source': 'src/a', 'destination': 'a/./a.txt', 'sha256': h(b'a')}]}, m.open('w'))
    entries = load_deploy_manifest(str(m))
    assert [e.destination for e in entries] == ['a/a.txt', 'b.txt']
    assert [Path(e.source).name for e in entries] == ['a', 'b']
'''),
        ('parent_traversal_rejected', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); s = base / 's'; s.write_bytes(b'x')
    m = base / 'm.json'; json.dump({'files': [{'source': str(s), 'destination': 'a/../../escape', 'sha256': h(b'x')}]}, m.open('w'))
    try: load_deploy_manifest(str(m))
    except ValueError: pass
    else: raise AssertionError('expected ValueError')
'''),
        ('duplicate_normalized_destination_rejected', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); s = base / 's'; s.write_bytes(b'x')
    m = base / 'm.json'; json.dump({'files': [{'source': str(s), 'destination': 'a/./b', 'sha256': h(b'x')}, {'source': str(s), 'destination': 'a/b', 'sha256': h(b'x')}]}, m.open('w'))
    try: load_deploy_manifest(str(m))
    except ValueError: pass
    else: raise AssertionError('expected duplicate rejection')
'''),
        ('absolute_destination_rejected', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); s = base / 's'; s.write_bytes(b'x')
    m = base / 'm.json'; json.dump({'files': [{'source': str(s), 'destination': '/abs', 'sha256': h(b'x')}]}, m.open('w'))
    try: load_deploy_manifest(str(m))
    except ValueError: pass
    else: raise AssertionError('expected absolute rejection')
'''),
        ('sha256_lowercase_length_validation', r'''
import json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
with tempfile.TemporaryDirectory() as td:
    base = Path(td); s = base / 's'; s.write_bytes(b'x')
    for bad in ['0' * 63, 'A' * 64]:
        m = base / (bad[0] + 'm.json'); json.dump({'files': [{'source': str(s), 'destination': 'file' + bad[0], 'sha256': bad}]}, m.open('w'))
        try: load_deploy_manifest(str(m))
        except ValueError: pass
        else: raise AssertionError('expected sha256 rejection')
'''),
        ('manifest_object_files_and_relative_sources', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); (base / 'rel').mkdir(); (base / 'rel' / 's').write_bytes(b'x')
    m = base / 'm.json'; json.dump({'files': [{'source': 'rel/s', 'destination': 'x', 'sha256': h(b'x')}]}, m.open('w'))
    e = load_deploy_manifest(str(m))[0]
    assert Path(e.source).is_absolute()
    assert e.destination == 'x'
'''),
        ('read_only_state_check', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
def snap(p):
    return sorted((x.relative_to(p).as_posix(), h(x.read_bytes()) if x.is_file() else 'dir') for x in Path(p).rglob('*'))
with tempfile.TemporaryDirectory() as td:
    base = Path(td); (base / 'src').mkdir(); (base / 'src' / 's').write_bytes(b'x')
    m = base / 'm.json'; json.dump({'files': [{'source': 'src/s', 'destination': 'x', 'sha256': h(b'x')}]}, m.open('w'))
    before = snap(base); load_deploy_manifest(str(m)); after = snap(base)
    assert before == after
'''),
    ]


def step2_cases():
    return [
        ('new_file_copy_plan_fields', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'dir/file.txt', h(b'new'))])
    assert len(ops) == 1
    op = ops[0]
    assert (op.op_id, op.destination, op.temp_path, op.backup_path, op.previous_sha256, tuple(op.directories)) == ('op-0001', 'dir/file.txt', '.tdf-tmp/0001-dir__file.txt.tmp', None, None, ('dir',))
'''),
        ('unchanged_file_noop_by_digest', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'same').write_bytes(b'same')
    src = base / 's'; src.write_bytes(b'same')
    assert plan_install(str(root), [ManifestEntry(str(src), 'same', h(b'same'))]) == []
'''),
        ('source_digest_mismatch_rejected', r'''
import tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'actual')
    try: plan_install(str(root), [ManifestEntry(str(src), 'x', '0' * 64)])
    except ValueError: pass
    else: raise AssertionError('expected digest mismatch')
'''),
        ('changed_same_size_file_requires_operation', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'ABCDEF')
    src = base / 's'; src.write_bytes(b'abcdef')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'abcdef'))])
    assert len(ops) == 1
    assert ops[0].previous_sha256 == h(b'ABCDEF')
'''),
        ('replaced_file_backup_path_contains_previous_digest', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old')
    src = base / 's'; src.write_bytes(b'new')
    op = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))])[0]
    assert op.backup_path == '.tdf-backup/0001-file-' + h(b'old') + '.bak'
'''),
        ('directory_creation_ordering_nested', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x')
    op = plan_install(str(root), [ManifestEntry(str(src), 'a/b/c/file', h(b'x'))])[0]
    assert tuple(op.directories) == ('a', 'a/b', 'a/b/c')
'''),
        ('read_only_state_check', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
def snap(p): return sorted((x.relative_to(p).as_posix(), h(x.read_bytes()) if x.is_file() else 'dir') for x in Path(p).rglob('*'))
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x')
    before = snap(root); plan_install(str(root), [ManifestEntry(str(src), 'nested/file', h(b'x'))]); after = snap(root)
    assert before == after == []
'''),
    ]


def step3_cases():
    return [
        ('write_intent_log_deterministic_schema_sorted', r'''
import json, tempfile
from pathlib import Path
from posix_manifest_installer import InstallOp, write_intent_log
with tempfile.TemporaryDirectory() as td:
    log = Path(td) / 'intent.json'
    ops = [InstallOp('op-0002', 'b', '/s2', '2' * 64, '.tdf-tmp/b', None, None), InstallOp('op-0001', 'a', '/s1', '1' * 64, '.tdf-tmp/a', None, None)]
    write_intent_log(str(log), ops)
    text = log.read_text()
    data = json.loads(text)
    assert text[-1:] == chr(10)
    assert data['schema_version'] == '1.0'
    assert [op['op_id'] for op in data['operations']] == ['op-0001', 'op-0002']
'''),
        ('replay_completes_pending_copy_new_file', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'd/file', h(b'x'))]); log = base / 'log.json'; write_intent_log(str(log), ops)
    assert replay_intent_log(str(root), str(log)) == ['op-0001']
    assert (root / 'd' / 'file').read_bytes() == b'x'
'''),
        ('second_replay_is_idempotent', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'x'))]); log = base / 'log.json'; write_intent_log(str(log), ops)
    replay_intent_log(str(root), str(log))
    assert replay_intent_log(str(root), str(log)) == ['op-0001']
'''),
        ('replay_replaced_file_creates_valid_backup', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old')
    src = base / 's'; src.write_bytes(b'new'); ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops)
    replay_intent_log(str(root), str(log))
    backup = root / ops[0].backup_path
    assert backup.read_bytes() == b'old'
    assert (root / 'file').read_bytes() == b'new'
'''),
        ('impossible_missing_destination_needing_backup_raises', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import InstallOp, RecoveryError, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'new'); log = base / 'log.json'
    write_intent_log(str(log), [InstallOp('op-0001', 'file', str(src), h(b'new'), '.tdf-tmp/file.tmp', '.tdf-backup/file.bak', h(b'old'))])
    try: replay_intent_log(str(root), str(log))
    except RecoveryError: pass
    else: raise AssertionError('expected RecoveryError')
'''),
        ('source_digest_mismatch_raises_recovery_error', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import InstallOp, RecoveryError, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'bad'); log = base / 'log.json'
    write_intent_log(str(log), [InstallOp('op-0001', 'file', str(src), h(b'good'), '.tdf-tmp/file.tmp', None, None)])
    try: replay_intent_log(str(root), str(log))
    except RecoveryError: pass
    else: raise AssertionError('expected RecoveryError')
'''),
        ('read_only_completed_replay_state_check', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
def snap(p): return sorted((x.relative_to(p).as_posix(), h(x.read_bytes()) if x.is_file() else 'dir') for x in Path(p).rglob('*'))
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'x'))]); log = base / 'log.json'; write_intent_log(str(log), ops)
    replay_intent_log(str(root), str(log)); before = snap(root); replay_intent_log(str(root), str(log)); after = snap(root)
    assert before == after
'''),
    ]


def step4_cases():
    return [
        ('rollback_restores_replaced_file_action_after_replay', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log))
    plan = plan_rollback(str(root), str(log))
    assert plan.errors == ()
    assert plan.actions[0]['action'] == 'restore' and plan.actions[0]['sha256'] == h(b'old')
'''),
        ('rollback_new_file_delete_action', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log))
    assert plan_rollback(str(root), str(log)).actions[0] == {'op_id': 'op-0001', 'action': 'delete', 'destination': 'file'}
'''),
        ('missing_backup_reported', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log)); (root / ops[0].backup_path).unlink()
    assert plan_rollback(str(root), str(log)).errors[0]['error'] == 'missing-backup'
'''),
        ('corrupted_backup_digest_mismatch_reported', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log)); (root / ops[0].backup_path).write_bytes(b'evil')
    plan = plan_rollback(str(root), str(log))
    assert plan.actions == ()
    assert plan.errors[0]['error'] == 'backup-digest-mismatch'
'''),
        ('rollback_reverse_operation_order', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'a').write_bytes(b'old-a'); (root / 'b').write_bytes(b'old-b')
    sa = base / 'sa'; sb = base / 'sb'; sa.write_bytes(b'new-a'); sb.write_bytes(b'new-b')
    ops = plan_install(str(root), [ManifestEntry(str(sb), 'b', h(b'new-b')), ManifestEntry(str(sa), 'a', h(b'new-a'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log))
    assert [a['op_id'] for a in plan_rollback(str(root), str(log)).actions] == ['op-0002', 'op-0001']
'''),
        ('invalid_log_raises_recovery_error', r'''
import json, tempfile
from pathlib import Path
from posix_manifest_installer import RecoveryError, plan_rollback
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); log = base / 'bad.json'; json.dump({'bad': []}, log.open('w'))
    try: plan_rollback(str(root), str(log))
    except RecoveryError: pass
    else: raise AssertionError('expected RecoveryError')
'''),
        ('read_only_state_check', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
def snap(p): return sorted((x.relative_to(p).as_posix(), h(x.read_bytes()) if x.is_file() else 'dir') for x in Path(p).rglob('*'))
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log))
    before = snap(root); plan_rollback(str(root), str(log)); after = snap(root)
    assert before == after
'''),
    ]


def step5_cases():
    return [
        ('clean_install_audit_returns_plan_without_recovery', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import audit_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x'); m = base / 'm.json'
    json.dump({'files': [{'source': str(src), 'destination': 'file', 'sha256': h(b'x')}]}, m.open('w'))
    r = audit_install(str(root), str(m), str(base / 'missing.json'))
    assert r.recovered_operation_ids == ()
    assert len(r.install_operations) == 1
    assert r.rollback_plan.actions == () and r.rollback_plan.errors == ()
    assert not (root / 'file').exists()
'''),
        ('partial_install_recovery_before_fresh_plan', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, audit_install, plan_install, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new'); m = base / 'm.json'
    json.dump({'files': [{'source': str(src), 'destination': 'file', 'sha256': h(b'new')}]}, m.open('w'))
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops)
    r = audit_install(str(root), str(m), str(log))
    assert r.recovered_operation_ids == ('op-0001',)
    assert r.install_operations == ()
    assert (root / 'file').read_bytes() == b'new'
'''),
        ('regression_step1_traversal_rejected', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import load_deploy_manifest
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); s = base / 's'; s.write_bytes(b'x'); m = base / 'm.json'
    json.dump({'files': [{'source': str(s), 'destination': '../escape', 'sha256': h(b'x')}]}, m.open('w'))
    try: load_deploy_manifest(str(m))
    except ValueError: pass
    else: raise AssertionError('expected traversal rejection')
'''),
        ('regression_step2_same_size_changed_requires_plan', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'ABCDEF'); src = base / 's'; src.write_bytes(b'abcdef')
    assert len(plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'abcdef'))])) == 1
'''),
        ('regression_step3_second_replay_idempotent', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'x'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log))
    assert replay_intent_log(str(root), str(log)) == ['op-0001']
'''),
        ('regression_step4_corrupt_backup_error', r'''
import hashlib, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new')
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops); replay_intent_log(str(root), str(log)); (root / ops[0].backup_path).write_bytes(b'evil')
    assert plan_rollback(str(root), str(log)).errors[0]['error'] == 'backup-digest-mismatch'
'''),
        ('rollback_after_recovery_has_restore_action', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import ManifestEntry, audit_install, plan_install, write_intent_log
def h(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); (root / 'file').write_bytes(b'old'); src = base / 's'; src.write_bytes(b'new'); m = base / 'm.json'
    json.dump({'files': [{'source': str(src), 'destination': 'file', 'sha256': h(b'new')}]}, m.open('w'))
    ops = plan_install(str(root), [ManifestEntry(str(src), 'file', h(b'new'))]); log = base / 'log.json'; write_intent_log(str(log), ops)
    r = audit_install(str(root), str(m), str(log))
    assert r.rollback_plan.errors == ()
    assert r.rollback_plan.actions[0]['action'] == 'restore'
'''),
        ('read_only_without_log_does_not_modify_root', r'''
import hashlib, json, tempfile
from pathlib import Path
from posix_manifest_installer import audit_install
def h(b): return hashlib.sha256(b).hexdigest()
def snap(p): return sorted((x.relative_to(p).as_posix(), h(x.read_bytes()) if x.is_file() else 'dir') for x in Path(p).rglob('*'))
with tempfile.TemporaryDirectory() as td:
    base = Path(td); root = base / 'root'; root.mkdir(); src = base / 's'; src.write_bytes(b'x'); m = base / 'm.json'
    json.dump({'files': [{'source': str(src), 'destination': 'dir/file', 'sha256': h(b'x')}]}, m.open('w'))
    before = snap(root); audit_install(str(root), str(m), str(base / 'none.json')); after = snap(root)
    assert before == after == []
'''),
    ]
