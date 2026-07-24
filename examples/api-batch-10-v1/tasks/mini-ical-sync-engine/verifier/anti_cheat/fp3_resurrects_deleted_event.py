#!/usr/bin/env python3
from pathlib import Path
import os

root = Path(os.environ.get('TDF_WORKSPACE', '.'))
target = root / 'environment' / 'codebase' / 'mini_ical_sync_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old_guard = '            if tomb and not _newer(change.event.sequence, change.event.updated, tomb[0], tomb[1]):\n                continue\n'
new_guard = '            if False and tomb and not _newer(change.event.sequence, change.event.updated, tomb[0], tomb[1]):\n                continue\n'
old_current = '            if current is None or _newer(change.event.sequence, change.event.updated, current.sequence, current.updated):\n'
new_current = '            if current is None or current.status == "CANCELLED" or _newer(change.event.sequence, change.event.updated, current.sequence, current.updated):\n'
if old_guard not in text or old_current not in text:
    raise SystemExit('fp3 exact tombstone precedence patterns not found')
text = text.replace(old_guard, new_guard, 1)
text = text.replace(old_current, new_current, 1)
target.write_text(text, encoding='utf-8')
