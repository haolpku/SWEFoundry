#!/usr/bin/env python3
import os
import pathlib
import sys

root = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = root / 'environment' / 'codebase' / 'wasm_auditor' / 'migration.py'
text = path.read_text(encoding='utf-8')
old = "    for section in sections:\n        if section.id in _FEATURE_SECTIONS:\n"
new = "    for section in sections:\n        object.__setattr__(section, 'payload', section.payload + b'\\x00')\n        if section.id in _FEATURE_SECTIONS:\n"
if old not in text:
    print('fp4 pattern not found', file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
