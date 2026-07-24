#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = workspace / 'environment' / 'codebase' / 'png_asset_pipeline' / 'metadata.py'
text = path.read_text(encoding='utf-8')
old = "    for key, value in sorted(pairs, key=lambda item: (item[0], item[1])):\n        if key not in canonical:\n            canonical[key] = value\n"
new = "    for key, value in pairs:\n        if key not in canonical:\n            canonical[key] = value\n"
if old not in text:
    raise SystemExit('fp3 exact oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
