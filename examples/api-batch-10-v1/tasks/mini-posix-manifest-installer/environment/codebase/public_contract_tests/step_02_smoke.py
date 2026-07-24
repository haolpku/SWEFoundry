#!/usr/bin/env python3
import hashlib
import sys
import tempfile
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from posix_manifest_installer import ManifestEntry, plan_install


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
    assert len(ops) == 1
    op = ops[0]
    assert op.op_id == 'op-0001'
    assert op.destination == 'dir/file.txt'
    assert op.temp_path == '.tdf-tmp/0001-dir__file.txt.tmp'
    assert op.backup_path is None
    assert op.previous_sha256 is None
    assert tuple(op.directories) == ('dir',)
    assert not (root / 'dir').exists()

    (root / 'dir').mkdir()
    (root / 'dir' / 'file.txt').write_bytes(b'payload')
    assert plan_install(str(root), [entry]) == []
