#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ws = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = ws / 'environment' / 'codebase' / 'posix_manifest_installer' / 'installer.py'
text = path.read_text(encoding='utf-8')
old = '''if os.path.exists(dest) and _sha256_file(dest) == wanted:
            completed.append(op["op_id"])
            continue'''
new = '''if os.path.exists(dest) and _sha256_file(dest) == wanted:
            raise RecoveryError(f"already completed for {op['op_id']}")'''
if old not in text:
    raise SystemExit('fp3 exact Oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
