#!/usr/bin/env python3
import json
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from crdtnotebook import parse_notebook_ops, validate_notebook_dag

missing = parse_notebook_ops(json.dumps([
    {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A', 'deps': ['ghost:1']},
]))
problems = validate_notebook_dag(missing)
assert any(problem.code == 'missing_dependency' and problem.witness == ('a:1', 'ghost:1') for problem in problems)

cycle = parse_notebook_ops(json.dumps([
    {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A', 'deps': ['b:1']},
    {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['a:1']},
]))
problems = validate_notebook_dag(cycle)
assert any(problem.code == 'causal_cycle' and problem.witness == ('a:1', 'b:1') for problem in problems)
