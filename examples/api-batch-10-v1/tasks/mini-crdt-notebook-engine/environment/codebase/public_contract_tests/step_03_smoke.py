#!/usr/bin/env python3
import json
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from crdtnotebook import merge_notebook_text, parse_notebook_ops

ops = parse_notebook_ops(json.dumps([
    {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B'},
    {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'},
    {'actor': 'c', 'seq': 1, 'type': 'delete', 'target': 'a:1', 'deps': ['a:1']},
]))
cells = merge_notebook_text(ops)
assert len(cells) == 1
assert cells[0].cell_id == 'main'
assert cells[0].text == 'B'
assert cells[0].tombstones == ('a:1',)
