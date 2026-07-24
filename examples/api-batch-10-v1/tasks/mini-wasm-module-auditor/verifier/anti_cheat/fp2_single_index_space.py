#!/usr/bin/env python3
import os
import pathlib
import sys

root = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = root / 'environment' / 'codebase' / 'wasm_auditor' / 'symbols.py'
text = path.read_text(encoding='utf-8')
old = "        index = indexes[kind]\n        indexes[kind] += 1\n"
new = "        index = sum(indexes.values())\n        indexes[kind] += 1\n"
if old not in text:
    print('fp2 pattern not found', file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
