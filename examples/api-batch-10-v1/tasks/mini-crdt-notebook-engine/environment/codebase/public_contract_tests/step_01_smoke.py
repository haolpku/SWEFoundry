#!/usr/bin/env python3
import json
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from crdtnotebook import parse_notebook_ops

records = [
    {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B'},
    {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'},
]
ops = parse_notebook_ops(json.dumps(records))
assert [op.op_id for op in ops] == ['a:1', 'b:1']
assert [op.char for op in ops] == ['A', 'B']

try:
    parse_notebook_ops(json.dumps(records + [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'Z'}]))
except Exception as exc:
    assert 'duplicate' in str(exc).lower() or exc.__class__.__name__.endswith('Error')
else:
    raise AssertionError('duplicate actor sequence must raise')
