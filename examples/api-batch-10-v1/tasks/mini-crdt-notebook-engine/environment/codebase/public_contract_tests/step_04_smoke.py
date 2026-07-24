#!/usr/bin/env python3
import json
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from crdtnotebook import parse_notebook_ops, plan_notebook_compaction

ops = parse_notebook_ops(json.dumps([
    {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'},
    {'actor': 'b', 'seq': 1, 'type': 'delete', 'target': 'a:1', 'deps': ['a:1']},
    {'actor': 'c', 'seq': 1, 'type': 'checkpoint', 'covers': ['a:1', 'b:1'], 'deps': ['b:1']},
]))
plan = plan_notebook_compaction(ops, {'peer2': ['b:1'], 'peer1': ['c:1']})
assert plan.stable_tombstones == ('a:1',)
assert 'a:1' not in plan.retained_operations
assert 'compact tombstone a:1' in plan.actions
