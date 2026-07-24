#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import py_compile

ROOT = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
ENGINE = ROOT / 'environment' / 'codebase' / 'crdtnotebook' / 'engine.py'
PATTERN = '''    cells: tuple[NotebookCell, ...]
    if problems:
        cells = ()
    else:
        cells = tuple(merge_notebook_text(list(ops)))
'''
REPLACEMENT = '''    visible_by_cell: dict[str, list[str]] = {}
    for op in ops:
        if op.op_type == "insert":
            visible_by_cell.setdefault(op.cell or "", []).append(op.char or "")
    cells = tuple(NotebookCell(cell, "".join(chars), "", ()) for cell, chars in sorted(visible_by_cell.items()))
'''
text = ENGINE.read_text(encoding='utf-8')
if PATTERN not in text:
    raise SystemExit('fp5 exact Oracle pattern not found')
ENGINE.write_text(text.replace(PATTERN, REPLACEMENT, 1), encoding='utf-8')
py_compile.compile(str(ENGINE), doraise=True)
