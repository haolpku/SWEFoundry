#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import py_compile

ROOT = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
ENGINE = ROOT / 'environment' / 'codebase' / 'crdtnotebook' / 'engine.py'
PATTERN = '''def parse_notebook_ops(text: str) -> list[NotebookOp]:
    seen: set[str] = set()
    ops: list[NotebookOp] = []
    for record in _load_records(text):
        op = _make_op(record)
        if op.op_id in seen:
            raise NotebookValidationError(f"duplicate operation id {op.op_id}")
        seen.add(op.op_id)
        ops.append(op)
    return sorted(ops, key=lambda op: (op.actor, op.seq))
'''
REPLACEMENT = '''def parse_notebook_ops(text: str) -> list[NotebookOp]:
    seen: dict[str, NotebookOp] = {}
    for record in _load_records(text):
        op = _make_op(record)
        seen[op.op_id] = op
    return sorted(seen.values(), key=lambda op: (op.actor, op.seq))
'''
text = ENGINE.read_text(encoding='utf-8')
if PATTERN not in text:
    raise SystemExit('fp1 exact Oracle pattern not found')
ENGINE.write_text(text.replace(PATTERN, REPLACEMENT, 1), encoding='utf-8')
py_compile.compile(str(ENGINE), doraise=True)
