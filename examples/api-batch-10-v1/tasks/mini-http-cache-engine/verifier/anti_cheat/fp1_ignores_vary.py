#!/usr/bin/env python3
import os
import pathlib
import sys

workspace = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
target = workspace / 'environment' / 'codebase' / 'mini_http_cache_engine' / 'core.py'
text = target.read_text(encoding='utf-8')
old = 'return canonical_key(request, response, include_vary=True)'
new = 'return canonical_key(request, response, include_vary=False)'
if text.count(old) != 1:
    print('fp1_ignores_vary expected exactly one complete-Oracle pattern', file=sys.stderr)
    raise SystemExit(2)
target.write_text(text.replace(old, new, 1), encoding='utf-8')
