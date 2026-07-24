#!/usr/bin/env python3
import hashlib
import json
import sys
import tempfile
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from posix_manifest_installer import ManifestEntry, audit_install, plan_install, write_intent_log


def digest(data):
    return hashlib.sha256(data).hexdigest()

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    root = base / 'root'
    root.mkdir()
    source = base / 'payload.txt'
    source.write_bytes(b'payload')
    manifest = base / 'manifest.json'
    json.dump({'files': [{'source': str(source), 'destination': 'file.txt', 'sha256': digest(b'payload')}]}, manifest.open('w', encoding='utf-8'))
    report = audit_install(str(root), str(manifest), str(base / 'missing-log.json'))
    assert report.recovered_operation_ids == ()
    assert len(report.install_operations) == 1

    (root / 'file.txt').write_bytes(b'old')
    ops = plan_install(str(root), [ManifestEntry(str(source), 'file.txt', digest(b'payload'))])
    log = base / 'intent.json'
    write_intent_log(str(log), ops)
    recovered = audit_install(str(root), str(manifest), str(log))
    assert recovered.recovered_operation_ids == ('op-0001',)
    assert recovered.install_operations == ()
    assert (root / 'file.txt').read_bytes() == b'payload'
    assert recovered.rollback_plan.actions[0]['action'] == 'restore'
