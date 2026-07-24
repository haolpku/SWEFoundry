#!/usr/bin/env python3
import os
import pathlib
import sys

root = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = root / 'environment' / 'codebase' / 'wasm_auditor' / 'validation.py'
text = path.read_text(encoding='utf-8')
old = "        if section.id == 0:\n            continue\n        if section.id in seen:\n"
new = "        if section.id == 0:\n            pass\n        if section.id in seen:\n"
if old not in text:
    print('fp3 pattern not found', file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
