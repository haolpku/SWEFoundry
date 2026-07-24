#!/usr/bin/env python3
import os
import pathlib
import sys

workspace = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
target = workspace / 'environment' / 'codebase' / 'mini_http_cache_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = 'return audit_snapshot(snapshot_path, events, now, validate_first=True)'
new = 'return audit_snapshot(snapshot_path, events, now, validate_first=False)'
if text.count(old) != 1:
    print('fp5_replays_before_snapshot_validation expected exactly one complete-Oracle pattern', file=sys.stderr)
    raise SystemExit(2)
target.write_text(text.replace(old, new, 1), encoding='utf-8')
