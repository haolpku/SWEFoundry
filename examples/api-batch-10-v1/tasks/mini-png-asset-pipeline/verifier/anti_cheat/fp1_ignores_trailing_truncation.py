#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = workspace / 'environment' / 'codebase' / 'png_asset_pipeline' / 'chunks.py'
text = path.read_text(encoding='utf-8')
old = "        if data_end > len(data):\n            raise PngFormatError(\"truncated chunk data\")\n        if crc_end > len(data):\n            raise PngFormatError(\"truncated chunk CRC\")\n        crc = struct.unpack(\">I\", data[data_end:crc_end])[0]\n"
new = "        if data_end > len(data):\n            data_end = len(data)\n            crc_end = len(data)\n        if crc_end > len(data):\n            crc_end = len(data)\n        crc = struct.unpack(\">I\", data[data_end:crc_end].ljust(4, b\"\\x00\"))[0]\n"
if old not in text:
    raise SystemExit('fp1 exact oracle pattern not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
