#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = workspace / 'environment' / 'codebase' / 'png_asset_pipeline' / 'audit.py'
text = path.read_text(encoding='utf-8')
old1 = "    problems = validate_png_chunks(chunks)\n"
new1 = "    problems = []\n"
old2 = "    cleanup_actions = plan_png_cleanup(chunks)\n"
new2 = "    cleanup_actions = []\n"
if old1 not in text or old2 not in text:
    raise SystemExit('fp5 exact oracle pattern not found')
text = text.replace(old1, new1, 1).replace(old2, new2, 1)
path.write_text(text, encoding='utf-8')
