#!/usr/bin/env python3
from pathlib import Path
import os

root = Path(os.environ.get('TDF_WORKSPACE', '.'))
target = root / 'environment' / 'codebase' / 'mini_ical_sync_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = '            winner = max(group, key=lambda e: (e.sequence, e.updated, 1 if e.status == "CANCELLED" else 0, e.uid, e.recurrence_id, e.dtstart, e.summary))\n'
new = '            winner = group[0]\n'
if old not in text:
    raise SystemExit('fp4 exact conflict winner pattern not found')
target.write_text(text.replace(old, new, 1), encoding='utf-8')
