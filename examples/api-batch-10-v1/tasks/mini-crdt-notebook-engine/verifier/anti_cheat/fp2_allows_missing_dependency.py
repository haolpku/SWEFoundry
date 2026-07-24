#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import py_compile

ROOT = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
ENGINE = ROOT / 'environment' / 'codebase' / 'crdtnotebook' / 'engine.py'
PATTERN = '''        for ref in refs:
            if ref not in by_id:
                code = "checkpoint_missing" if op.op_type == "checkpoint" and ref in op.covers else "missing_dependency"
                problems.append(CrdtProblem(code, op.op_id, f"referenced operation {ref} is absent", (op.op_id, ref)))
'''
REPLACEMENT = '''        for ref in refs:
            if ref not in by_id and op.op_type == "checkpoint" and ref in op.covers:
                code = "checkpoint_missing"
                problems.append(CrdtProblem(code, op.op_id, f"referenced operation {ref} is absent", (op.op_id, ref)))
'''
text = ENGINE.read_text(encoding='utf-8')
if PATTERN not in text:
    raise SystemExit('fp2 exact Oracle pattern not found')
ENGINE.write_text(text.replace(PATTERN, REPLACEMENT, 1), encoding='utf-8')
py_compile.compile(str(ENGINE), doraise=True)
