#!/usr/bin/env python3
import hashlib
import json
import sys
import tempfile
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from posix_manifest_installer import load_deploy_manifest


def digest(data):
    return hashlib.sha256(data).hexdigest()

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    (base / 'src').mkdir()
    (base / 'src' / 'a.txt').write_bytes(b'alpha')
    (base / 'src' / 'b.txt').write_bytes(b'beta')
    manifest = base / 'manifest.json'
    json.dump({'files': [
        {'source': 'src/b.txt', 'destination': 'z/../b.txt', 'sha256': digest(b'beta')},
        {'source': 'src/a.txt', 'destination': 'a/./a.txt', 'sha256': digest(b'alpha')},
    ]}, manifest.open('w', encoding='utf-8'))
    entries = load_deploy_manifest(str(manifest))
    assert [e.destination for e in entries] == ['a/a.txt', 'b.txt']
    assert all(Path(e.source).is_absolute() for e in entries)

    bad = base / 'bad.json'
    json.dump({'files': [{'source': 'src/a.txt', 'destination': '../escape.txt', 'sha256': digest(b'alpha')}]}, bad.open('w', encoding='utf-8'))
    try:
        load_deploy_manifest(str(bad))
    except ValueError:
        pass
    else:
        raise AssertionError('parent traversal destination was accepted')
