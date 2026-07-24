#!/usr/bin/env python3
import os
import pathlib
import sys

workspace = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
target = workspace / 'environment' / 'codebase' / 'mini_http_cache_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = 'return evaluate_entry(entry, now, max_age_precedence=True)'
new = 'return evaluate_entry(entry, now, max_age_precedence=False)'
if text.count(old) != 1:
    print('fp2_expires_over_max_age expected exactly one complete-Oracle pattern', file=sys.stderr)
    raise SystemExit(2)
target.write_text(text.replace(old, new, 1), encoding='utf-8')
