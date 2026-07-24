#!/usr/bin/env python3
import os
import pathlib
import sys

workspace = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
target = workspace / 'environment' / 'codebase' / 'mini_http_cache_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = 'return invalidate_entries(entries, event, all_variants=True)'
new = 'return invalidate_entries(entries, event, all_variants=False)'
if text.count(old) != 1:
    print('fp4_invalidates_only_exact_key expected exactly one complete-Oracle pattern', file=sys.stderr)
    raise SystemExit(2)
target.write_text(text.replace(old, new, 1), encoding='utf-8')
