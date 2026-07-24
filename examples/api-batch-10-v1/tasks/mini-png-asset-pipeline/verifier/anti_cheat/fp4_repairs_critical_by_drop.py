#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = workspace / 'environment' / 'codebase' / 'png_asset_pipeline' / 'cleanup.py'
text = path.read_text(encoding='utf-8')
old = "            if _is_critical(chunk.type):\n                actions.append(PngCleanupAction(chunk.offset, \"cannot_remove\", chunk.type, \"corrupt critical chunk\", (\"repair source bytes before rewriting\",)))\n            else:\n                actions.append(PngCleanupAction(chunk.offset, \"repair_crc\", chunk.type, \"CRC mismatch\", (f\"expected={actual_crc:08x}\", f\"stored={chunk.crc:08x}\")))\n"
new = "            if _is_critical(chunk.type):\n                actions.append(PngCleanupAction(chunk.offset, \"remove\", chunk.type, \"corrupt critical chunk\", (\"unsafe critical drop\",)))\n            else:\n                actions.append(PngCleanupAction(chunk.offset, \"repair_crc\", chunk.type, \"CRC mismatch\", (f\"expected={actual_crc:08x}\", f\"stored={chunk.crc:08x}\")))\n"
if old not in text:
    raise SystemExit('fp4 exact oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
