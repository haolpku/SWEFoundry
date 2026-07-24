#!/usr/bin/env python3
import hashlib
import sys
import tempfile
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from posix_manifest_installer import ManifestEntry, plan_install, replay_intent_log, write_intent_log


def digest(data):
    return hashlib.sha256(data).hexdigest()

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    root = base / 'root'
    root.mkdir()
    source = base / 'payload.txt'
    source.write_bytes(b'payload')
    entry = ManifestEntry(str(source), 'dir/file.txt', digest(b'payload'))
    ops = plan_install(str(root), [entry])
    log = base / 'intent.json'
    write_intent_log(str(log), ops)
    assert replay_intent_log(str(root), str(log)) == ['op-0001']
    assert (root / 'dir' / 'file.txt').read_bytes() == b'payload'
    assert replay_intent_log(str(root), str(log)) == ['op-0001']
