#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = workspace / 'environment' / 'codebase' / 'png_asset_pipeline' / 'validation.py'
text = path.read_text(encoding='utf-8')
old = "        if _crc(chunk) != chunk.crc:\n            problems.append(PngProblem(chunk.offset, \"CRC_MISMATCH\", chunk.type, \"chunk CRC does not match type and data\"))\n"
new = "        if chunk.type[0].isupper() and _crc(chunk) != chunk.crc:\n            problems.append(PngProblem(chunk.offset, \"CRC_MISMATCH\", chunk.type, \"chunk CRC does not match type and data\"))\n"
if old not in text:
    raise SystemExit('fp2 exact oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
