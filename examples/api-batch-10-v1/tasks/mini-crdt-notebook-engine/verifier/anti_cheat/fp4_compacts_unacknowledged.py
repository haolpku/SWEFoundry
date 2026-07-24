#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import py_compile

ROOT = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
ENGINE = ROOT / 'environment' / 'codebase' / 'crdtnotebook' / 'engine.py'
PATTERN = '''    stable = tuple(sorted(target for target, delete_id in deleted.items() if target in all_seen and delete_id in all_seen))
'''
REPLACEMENT = '''    stable = tuple(sorted(target for target, delete_id in deleted.items() if target in all_seen))
'''
text = ENGINE.read_text(encoding='utf-8')
if PATTERN not in text:
    raise SystemExit('fp4 exact Oracle pattern not found')
ENGINE.write_text(text.replace(PATTERN, REPLACEMENT, 1), encoding='utf-8')
py_compile.compile(str(ENGINE), doraise=True)
