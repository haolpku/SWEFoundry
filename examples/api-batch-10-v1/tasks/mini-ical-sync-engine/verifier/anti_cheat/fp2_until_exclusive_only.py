#!/usr/bin/env python3
from pathlib import Path
import os

root = Path(os.environ.get('TDF_WORKSPACE', '.'))
target = root / 'environment' / 'codebase' / 'mini_ical_sync_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = '        if until is not None and current > until:\n'
new = '        if until is not None and current >= until:\n'
if old not in text:
    raise SystemExit('fp2 exact UNTIL inclusivity pattern not found')
target.write_text(text.replace(old, new, 1), encoding='utf-8')
