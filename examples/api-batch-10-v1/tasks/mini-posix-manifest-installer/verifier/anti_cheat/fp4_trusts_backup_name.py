#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ws = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = ws / 'environment' / 'codebase' / 'posix_manifest_installer' / 'installer.py'
text = path.read_text(encoding='utf-8')
old = '''digest = _sha256_file(backup)
        if digest != previous:
            errors.append({"op_id": op["op_id"], "error": "backup-digest-mismatch", "destination": destination, "backup_path": backup_rel})
            continue
        actions.append({"op_id": op["op_id"], "action": "restore", "destination": destination, "backup_path": backup_rel, "sha256": previous})'''
new = '''actions.append({"op_id": op["op_id"], "action": "restore", "destination": destination, "backup_path": backup_rel, "sha256": previous})'''
if old not in text:
    raise SystemExit('fp4 exact Oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
