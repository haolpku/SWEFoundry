#!/usr/bin/env python3
import os
import pathlib
import sys

root = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = root / 'environment' / 'codebase' / 'wasm_auditor' / 'parser.py'
text = path.read_text(encoding='utf-8')
old = "        if end > len(raw):\n            raise ValueError(\"truncated section payload\")\n        payload = raw[pos:end]\n"
new = "        if end > len(raw):\n            end = len(raw)\n        payload = raw[pos:end]\n"
if old not in text:
    print('fp1 pattern not found', file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
