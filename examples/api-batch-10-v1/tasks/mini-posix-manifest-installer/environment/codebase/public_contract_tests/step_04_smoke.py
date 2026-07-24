#!/usr/bin/env python3
import hashlib
import sys
import tempfile
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from posix_manifest_installer import ManifestEntry, plan_install, plan_rollback, replay_intent_log, write_intent_log


def digest(data):
    return hashlib.sha256(data).hexdigest()

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    root = base / 'root'
    root.mkdir()
    (root / 'file.txt').write_bytes(b'old')
    source = base / 'new.txt'
    source.write_bytes(b'new')
    entry = ManifestEntry(str(source), 'file.txt', digest(b'new'))
    ops = plan_install(str(root), [entry])
    log = base / 'intent.json'
    write_intent_log(str(log), ops)
    replay_intent_log(str(root), str(log))
    plan = plan_rollback(str(root), str(log))
    assert plan.errors == ()
    assert plan.actions[0]['action'] == 'restore'
    assert plan.actions[0]['sha256'] == digest(b'old')

    backup = root / plan.actions[0]['backup_path']
    backup.unlink()
    missing = plan_rollback(str(root), str(log))
    assert missing.errors[0]['error'] == 'missing-backup'
