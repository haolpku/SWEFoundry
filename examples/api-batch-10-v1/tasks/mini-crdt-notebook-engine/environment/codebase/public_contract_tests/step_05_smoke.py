#!/usr/bin/env python3
import json
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from crdtnotebook import audit_crdt_notebook

snapshot = json.dumps({'schema_version': '0.9', 'ops': [
    {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'},
]})
journal = json.dumps([
    {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B', 'deps': ['a:1']},
    {'actor': 'c', 'seq': 1, 'type': 'checkpoint', 'covers': ['a:1', 'b:1'], 'deps': ['b:1']},
])
report = audit_crdt_notebook(snapshot, journal, {'peer': ['c:1']})
assert report.schema_version == '1.0'
assert report.recovered_from_snapshot is True
assert report.migrated_snapshot is True
assert not report.problems
assert [(cell.cell_id, cell.text) for cell in report.cells] == [('main', 'AB')]
