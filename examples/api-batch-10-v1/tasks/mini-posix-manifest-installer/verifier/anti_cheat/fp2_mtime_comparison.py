#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ws = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = ws / 'environment' / 'codebase' / 'posix_manifest_installer' / 'installer.py'
text = path.read_text(encoding='utf-8')
old = '''previous = _sha256_file(dest_path) if os.path.exists(dest_path) else None
        if previous == entry.sha256:
            continue'''
new = '''previous = entry.sha256 if os.path.exists(dest_path) and os.path.getsize(dest_path) == os.path.getsize(entry.source) else None
        if previous == entry.sha256:
            continue'''
if old not in text:
    raise SystemExit('fp2 exact Oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
