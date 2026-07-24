#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ws = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = ws / 'environment' / 'codebase' / 'posix_manifest_installer' / 'installer.py'
text = path.read_text(encoding='utf-8')
old = '''recovered: list[str] = []
    if os.path.exists(log_path):
        recovered = replay_intent_log(root, log_path)
    entries = load_deploy_manifest(manifest_path)
    operations = plan_install(root, entries)'''
new = '''entries = load_deploy_manifest(manifest_path)
    operations = plan_install(root, entries)
    recovered: list[str] = []
    if os.path.exists(log_path):
        recovered = replay_intent_log(root, log_path)'''
if old not in text:
    raise SystemExit('fp5 exact Oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
