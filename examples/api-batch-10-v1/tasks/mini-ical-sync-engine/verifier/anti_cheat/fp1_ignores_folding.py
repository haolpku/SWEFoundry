#!/usr/bin/env python3
from pathlib import Path
import os

root = Path(os.environ.get('TDF_WORKSPACE', '.'))
target = root / 'environment' / 'codebase' / 'mini_ical_sync_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = '            lines[-1] += line[1:]\n'
new = '            lines.append(line[1:])\n'
if old not in text:
    raise SystemExit('fp1 exact folding pattern not found')
target.write_text(text.replace(old, new, 1), encoding='utf-8')
