from __future__ import annotations

import json
import pathlib

from verifier.helpers import assert_equal, assert_true, candidate_json


def _j(records: list[dict]) -> str:
    return json.dumps(records, sort_keys=True, separators=(',', ':'))


def _parse_summary(ws: pathlib.Path, text: str):
    return candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops
ops = parse_notebook_ops({text!r})
print(json.dumps([{{'id': op.op_id, 'actor': op.actor, 'seq': op.seq, 'type': op.op_type, 'deps': list(op.deps), 'cell': op.cell, 'char': op.char, 'after': op.after, 'target': op.target, 'title': op.title, 'covers': list(op.covers)}} for op in ops], sort_keys=True))
''')


def _problems(ws: pathlib.Path, records: list[dict]):
    return candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops, validate_notebook_dag
ops = parse_notebook_ops({_j(records)!r})
problems = validate_notebook_dag(ops)
print(json.dumps([{{'code': p.code, 'op_id': p.op_id, 'message': p.message, 'witness': list(p.witness)}} for p in problems], sort_keys=True))
''')


def _cells(ws: pathlib.Path, records: list[dict]):
    return candidate_json(ws, f'''
from crdtnotebook import merge_notebook_text, parse_notebook_ops
ops = parse_notebook_ops({_j(records)!r})
cells = merge_notebook_text(ops)
print(json.dumps([{{'cell_id': c.cell_id, 'text': c.text, 'title': c.title, 'tombstones': list(c.tombstones)}} for c in cells], sort_keys=True))
''')


def _plan(ws: pathlib.Path, records: list[dict], frontiers: dict[str, list[str]]):
    return candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops, plan_notebook_compaction
ops = parse_notebook_ops({_j(records)!r})
plan = plan_notebook_compaction(ops, {frontiers!r})
print(json.dumps({{'peer_frontiers': [[peer, list(ids)] for peer, ids in plan.peer_frontiers], 'stable_tombstones': list(plan.stable_tombstones), 'checkpoint_candidates': list(plan.checkpoint_candidates), 'retained_operations': list(plan.retained_operations), 'actions': list(plan.actions)}}, sort_keys=True))
''')


def _audit(ws: pathlib.Path, snapshot: str | None, journal_records: list[dict], frontiers: dict[str, list[str]]):
    return candidate_json(ws, f'''
from crdtnotebook import audit_crdt_notebook
report = audit_crdt_notebook({snapshot!r}, {_j(journal_records)!r}, {frontiers!r})
print(json.dumps({{'schema_version': report.schema_version, 'operations': [op.op_id for op in report.operations], 'problems': [{{'code': p.code, 'op_id': p.op_id, 'witness': list(p.witness)}} for p in report.problems], 'cells': [{{'cell_id': c.cell_id, 'text': c.text, 'title': c.title, 'tombstones': list(c.tombstones)}} for c in report.cells], 'plan': {{'stable_tombstones': list(report.compaction_plan.stable_tombstones), 'checkpoint_candidates': list(report.compaction_plan.checkpoint_candidates), 'retained_operations': list(report.compaction_plan.retained_operations), 'actions': list(report.compaction_plan.actions)}}, 'recovered': report.recovered_from_snapshot, 'migrated': report.migrated_snapshot}}, sort_keys=True))
''')


def s1_sort(ws):
    got = _parse_summary(ws, _j([{'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B'}, {'actor': 'a', 'seq': 2, 'type': 'insert', 'cell': 'c', 'char': 'A'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'a'}]))
    assert_equal([item['id'] for item in got], ['a:1', 'a:2', 'b:1'])


def s1_duplicate(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops
try:
    parse_notebook_ops({_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'Z'}])!r})
except Exception as exc:
    print(json.dumps({{'raised': True, 'type': type(exc).__name__, 'message': str(exc)}}, sort_keys=True))
else:
    print(json.dumps({{'raised': False}}, sort_keys=True))
''')
    assert_true(got['raised'], 'duplicate actor/seq must raise')


def s1_jsonl(ws):
    text = '\n'.join([json.dumps({'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B'}), json.dumps({'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'})])
    got = _parse_summary(ws, text)
    assert_equal([item['id'] for item in got], ['a:1', 'b:1'])


def s1_wrapped(ws):
    got = _parse_summary(ws, json.dumps({'journal': [{'actor': 'a', 'seq': 1, 'type': 'insert', 'obj': 'cell', 'char': 'Ω'}]}))
    assert_equal(got[0]['cell'], 'cell')
    assert_equal(got[0]['char'], 'Ω')


def s1_validation(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops
cases = [{_j([{'actor': '', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'}])!r}, {_j([{'actor': 'a', 'seq': True, 'type': 'insert', 'cell': 'c', 'char': 'A'}])!r}, {_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'XY'}])!r}]
raised = []
for text in cases:
    try:
        parse_notebook_ops(text)
    except Exception:
        raised.append(True)
    else:
        raised.append(False)
print(json.dumps({{'raised': raised}}, sort_keys=True))
''')
    assert_equal(got['raised'], [True, True, True])


def s1_normalizes(ws):
    got = _parse_summary(ws, _j([{'actor': 'a', 'seq': 1, 'type': 'checkpoint', 'covers': ['z:9', 'a:1']}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['z:9', 'a:1']}]))
    assert_equal(got[0]['covers'], ['a:1', 'z:9'])
    assert_equal(got[1]['deps'], ['a:1', 'z:9'])


def s1_delete_title(ws):
    got = _parse_summary(ws, _j([{'actor': 'a', 'seq': 1, 'type': 'delete', 'object': 'b:2', 'cell': 'c'}, {'actor': 'b', 'seq': 2, 'type': 'set-title', 'cell': 'c', 'title': 'Notebook'}]))
    assert_equal(got[0]['target'], 'b:2')
    assert_equal(got[1]['title'], 'Notebook')


def s1_readonly(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops
ops = parse_notebook_ops({_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'}])!r})
before = [op.op_id for op in ops]
try:
    ops[0].actor = 'mutated'
except Exception as exc:
    frozen = True
else:
    frozen = False
after = [op.op_id for op in ops]
print(json.dumps({{'frozen': frozen, 'before': before, 'after': after}}, sort_keys=True))
''')
    assert_true(got['frozen'], 'operation objects must be immutable')
    assert_equal(got['before'], got['after'])


def s2_missing(ws):
    got = _problems(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A', 'deps': ['ghost:1']}])
    assert_true({'code': 'missing_dependency', 'op_id': 'a:1', 'message': 'referenced operation ghost:1 is absent', 'witness': ['a:1', 'ghost:1']} in got, 'missing dependency witness absent')


def s2_checkpoint(ws):
    got = _problems(ws, [{'actor': 'a', 'seq': 1, 'type': 'checkpoint', 'covers': ['missing:7']}])
    assert_equal(got[0]['code'], 'checkpoint_missing')
    assert_equal(got[0]['witness'], ['a:1', 'missing:7'])


def s2_gap(ws):
    got = _problems(ws, [{'actor': 'a', 'seq': 2, 'type': 'insert', 'cell': 'c', 'char': 'A'}])
    assert_equal(got[0]['code'], 'sequence_gap')
    assert_equal(got[0]['witness'], ['a:1', 'a:2'])


def s2_cycle(ws):
    got = _problems(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A', 'deps': ['b:1']}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['a:1']}])
    assert_true(any(item['code'] == 'causal_cycle' and item['witness'] == ['a:1', 'b:1'] for item in got), 'canonical cycle witness missing')


def s2_sorted(ws):
    got = _problems(ws, [{'actor': 'b', 'seq': 2, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['no:1']}, {'actor': 'a', 'seq': 2, 'type': 'checkpoint', 'covers': ['ghost:1']}])
    assert_equal([(item['code'], item['op_id']) for item in got], sorted((item['code'], item['op_id']) for item in got))


def s2_valid(ws):
    got = _problems(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['a:1']}])
    assert_equal(got, [])


def s2_duplicate_regression(ws):
    s1_duplicate(ws)


def s2_readonly(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops, validate_notebook_dag
ops = parse_notebook_ops({_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A'}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['a:1']}])!r})
before = [(op.op_id, list(op.deps)) for op in ops]
validate_notebook_dag(ops)
after = [(op.op_id, list(op.deps)) for op in ops]
print(json.dumps({{'before': before, 'after': after}}, sort_keys=True))
''')
    assert_equal(got['before'], got['after'])


def s3_concurrent(ws):
    got = _cells(ws, [{'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}])
    assert_equal(got, [{'cell_id': 'main', 'text': 'AB', 'title': '', 'tombstones': []}])


def s3_input_order(ws):
    first = _cells(ws, [{'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}])
    second = _cells(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B'}])
    assert_equal(first, second)
    assert_equal(first[0]['text'], 'AB')


def s3_chain(ws):
    got = _cells(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'H'}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'i', 'after': 'a:1', 'deps': ['a:1']}])
    assert_equal(got[0]['text'], 'Hi')


def s3_delete(ws):
    got = _cells(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'X'}, {'actor': 'b', 'seq': 1, 'type': 'delete', 'target': 'a:1', 'deps': ['a:1']}])
    assert_equal(got, [{'cell_id': 'main', 'text': '', 'title': '', 'tombstones': ['a:1']}])


def s3_idempotent(ws):
    got = _cells(ws, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'X'}, {'actor': 'b', 'seq': 1, 'type': 'delete', 'target': 'a:1', 'deps': ['a:1']}, {'actor': 'c', 'seq': 1, 'type': 'delete', 'target': 'a:1', 'deps': ['a:1']}])
    assert_equal(got[0]['tombstones'], ['a:1'])
    assert_equal(got[0]['text'], '')


def s3_cells_titles(ws):
    got = _cells(ws, [{'actor': 'z', 'seq': 1, 'type': 'insert', 'cell': 'zcell', 'char': 'Z'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'acell', 'char': 'A'}, {'actor': 't', 'seq': 1, 'type': 'set-title', 'cell': 'acell', 'title': 'Alpha'}])
    assert_equal([cell['cell_id'] for cell in got], ['acell', 'zcell'])
    assert_equal(got[0]['title'], 'Alpha')


def s3_invalid(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import merge_notebook_text, parse_notebook_ops
ops = parse_notebook_ops({_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'X', 'deps': ['missing:1']}])!r})
try:
    merge_notebook_text(ops)
except Exception as exc:
    print(json.dumps({{'raised': True, 'type': type(exc).__name__}}, sort_keys=True))
else:
    print(json.dumps({{'raised': False}}, sort_keys=True))
''')
    assert_true(got['raised'], 'invalid DAG must not be merged')


def s3_readonly(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import merge_notebook_text, parse_notebook_ops
ops = parse_notebook_ops({_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}])!r})
before = [(op.op_id, op.char, op.cell) for op in ops]
merge_notebook_text(ops)
after = [(op.op_id, op.char, op.cell) for op in ops]
print(json.dumps({{'before': before, 'after': after}}, sort_keys=True))
''')
    assert_equal(got['before'], got['after'])


def _compaction_records():
    return [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}, {'actor': 'b', 'seq': 1, 'type': 'delete', 'target': 'a:1', 'deps': ['a:1']}, {'actor': 'c', 'seq': 1, 'type': 'checkpoint', 'covers': ['a:1', 'b:1'], 'deps': ['b:1']}]


def s4_stable(ws):
    got = _plan(ws, _compaction_records(), {'peer2': ['b:1'], 'peer1': ['c:1']})
    assert_equal(got['stable_tombstones'], ['a:1'])
    assert_true('a:1' not in got['retained_operations'], 'compacted source must not be retained')
    assert_equal(got['actions'], ['compact tombstone a:1'])


def s4_unseen(ws):
    got = _plan(ws, _compaction_records(), {'peer1': ['b:1'], 'peer2': ['a:1']})
    assert_equal(got['stable_tombstones'], [])
    assert_true('a:1' in got['retained_operations'], 'unseen delete must retain source operation')


def s4_frontiers(ws):
    got = _plan(ws, _compaction_records(), {'zpeer': ['c:1', 'b:1'], 'apeer': ['b:1']})
    assert_equal(got['peer_frontiers'], [['apeer', ['b:1']], ['zpeer', ['b:1', 'c:1']]])


def s4_checkpoint(ws):
    got = _plan(ws, _compaction_records(), {'peer1': ['c:1'], 'peer2': ['b:1']})
    assert_equal(got['checkpoint_candidates'], ['c:1'])


def s4_no_peers(ws):
    got = _plan(ws, _compaction_records(), {})
    assert_equal(got['stable_tombstones'], ['a:1'])


def s4_unknown(ws):
    got = _plan(ws, _compaction_records(), {'peer': ['missing:9', 'b:1']})
    assert_equal(got['stable_tombstones'], ['a:1'])


def s4_retained_sorted(ws):
    got = _plan(ws, _compaction_records(), {'peer': ['a:1']})
    assert_equal(got['retained_operations'], sorted(got['retained_operations']))


def s4_readonly(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import parse_notebook_ops, plan_notebook_compaction
frontiers = {{'peer': ['b:1']}}
ops = parse_notebook_ops({_j(_compaction_records())!r})
before = {{'ops': [op.op_id for op in ops], 'frontiers': {{k: list(v) for k, v in frontiers.items()}}}}
plan_notebook_compaction(ops, frontiers)
after = {{'ops': [op.op_id for op in ops], 'frontiers': {{k: list(v) for k, v in frontiers.items()}}}}
print(json.dumps({{'before': before, 'after': after}}, sort_keys=True))
''')
    assert_equal(got['before'], got['after'])


def s5_journal(ws):
    got = _audit(ws, None, _compaction_records(), {'peer': ['c:1']})
    assert_equal(got['schema_version'], '1.0')
    assert_equal(got['problems'], [])
    assert_equal(got['cells'][0]['tombstones'], ['a:1'])
    assert_equal(got['plan']['stable_tombstones'], ['a:1'])
    assert_equal(got['recovered'], False)


def s5_snapshot(ws):
    snapshot = json.dumps({'schema_version': '0.9', 'ops': [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}]}, sort_keys=True)
    got = _audit(ws, snapshot, [{'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B', 'deps': ['a:1']}], {'peer': ['b:1']})
    assert_equal(got['recovered'], True)
    assert_equal(got['migrated'], True)
    assert_equal(got['cells'], [{'cell_id': 'main', 'text': 'AB', 'title': '', 'tombstones': []}])


def s5_invalid_blocks(ws):
    got = _audit(ws, None, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'X', 'deps': ['missing:1']}], {'peer': ['a:1']})
    assert_true(any(problem['code'] == 'missing_dependency' for problem in got['problems']), 'missing dependency problem expected')
    assert_equal(got['cells'], [])


def s5_duplicate(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import audit_crdt_notebook
try:
    audit_crdt_notebook(None, {_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'Z'}])!r}, {{}})
except Exception as exc:
    print(json.dumps({{'raised': True, 'type': type(exc).__name__}}, sort_keys=True))
else:
    print(json.dumps({{'raised': False}}, sort_keys=True))
''')
    assert_true(got['raised'], 'audit must preserve duplicate rejection')


def s5_cycle(ws):
    got = _audit(ws, None, [{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'A', 'deps': ['b:1']}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'c', 'char': 'B', 'deps': ['a:1']}], {'peer': ['a:1']})
    assert_true(any(problem['code'] == 'causal_cycle' and problem['witness'] == ['a:1', 'b:1'] for problem in got['problems']), 'cycle regression missing')


def s5_merge_regression(ws):
    got = _audit(ws, None, [{'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B'}, {'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}], {'peer': ['a:1', 'b:1']})
    assert_equal(got['cells'][0]['text'], 'AB')


def s5_compaction_regression(ws):
    got = _audit(ws, None, _compaction_records(), {'peer1': ['b:1'], 'peer2': ['a:1']})
    assert_equal(got['plan']['stable_tombstones'], [])
    assert_true('a:1' in got['plan']['retained_operations'], 'unseen delete must retain source in integrated audit')


def s5_public_regressions(ws):
    s1_sort(ws)
    s2_missing(ws)
    s3_delete(ws)
    s4_unseen(ws)


def s5_readonly(ws):
    got = candidate_json(ws, f'''
from crdtnotebook import audit_crdt_notebook
frontiers = {{'peer': ['b:1']}}
journal = {_j([{'actor': 'a', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'A'}, {'actor': 'b', 'seq': 1, 'type': 'insert', 'cell': 'main', 'char': 'B', 'deps': ['a:1']}])!r}
before = {{k: list(v) for k, v in frontiers.items()}}
audit_crdt_notebook(None, journal, frontiers)
after = {{k: list(v) for k, v in frontiers.items()}}
print(json.dumps({{'before': before, 'after': after}}, sort_keys=True))
''')
    assert_equal(got['before'], got['after'])


CHECKS = {
    'step-1': [
        ('sorts_two_actor_inserts_by_actor_sequence', s1_sort),
        ('duplicate_actor_sequence_raises', s1_duplicate),
        ('newline_delimited_json_supported', s1_jsonl),
        ('object_wrapped_operations_supported', s1_wrapped),
        ('validates_actor_sequence_and_character_contract', s1_validation),
        ('normalizes_dependency_and_checkpoint_cover_order', s1_normalizes),
        ('delete_and_set_title_fields_are_normalized', s1_delete_title),
        ('read_only_state_check_operation_immutability', s1_readonly),
    ],
    'step-2': [
        ('missing_dependency_reported_with_stable_witness', s2_missing),
        ('checkpoint_missing_coverage_reported', s2_checkpoint),
        ('actor_sequence_gap_reported', s2_gap),
        ('causal_cycle_witness_deterministic', s2_cycle),
        ('problems_sorted_stably_by_dataclass_order', s2_sorted),
        ('valid_dag_has_no_problems', s2_valid),
        ('parse_duplicate_regression_still_raises', s2_duplicate_regression),
        ('read_only_state_check_validate_does_not_mutate_ops', s2_readonly),
    ],
    'step-3': [
        ('concurrent_inserts_ordered_by_operation_identifier', s3_concurrent),
        ('concurrent_insert_result_independent_of_input_order', s3_input_order),
        ('causal_after_chain_preserves_character_order', s3_chain),
        ('delete_removes_visible_character_and_keeps_tombstone', s3_delete),
        ('duplicate_deletes_are_idempotent', s3_idempotent),
        ('cells_sorted_by_identifier_and_titles_preserved', s3_cells_titles),
        ('invalid_dag_rejected_before_merge', s3_invalid),
        ('read_only_state_check_merge_does_not_mutate_ops', s3_readonly),
    ],
    'step-4': [
        ('stable_tombstone_compacted_when_all_peers_ack_delete', s4_stable),
        ('unseen_delete_keeps_tombstone_source_retained', s4_unseen),
        ('peer_frontiers_are_sorted_and_preserved', s4_frontiers),
        ('checkpoint_candidate_requires_covered_operations_seen', s4_checkpoint),
        ('no_peer_frontiers_uses_local_complete_closure', s4_no_peers),
        ('unknown_frontier_ids_are_ignored_safely', s4_unknown),
        ('retained_operations_are_stable_sorted_identifiers', s4_retained_sorted),
        ('read_only_state_check_compaction_does_not_mutate_inputs', s4_readonly),
    ],
    'step-5': [
        ('journal_only_audit_runs_full_pipeline', s5_journal),
        ('snapshot_schema_migration_recovers_combined_state', s5_snapshot),
        ('invalid_journal_missing_dependency_blocks_visible_cells', s5_invalid_blocks),
        ('duplicate_actor_sequence_regression_still_raises', s5_duplicate),
        ('causal_cycle_regression_reported_in_audit', s5_cycle),
        ('deterministic_merge_regression_preserved_in_audit', s5_merge_regression),
        ('compaction_regression_unseen_delete_retains_source', s5_compaction_regression),
        ('steps_one_to_four_public_regressions_remain_available', s5_public_regressions),
        ('read_only_state_check_audit_does_not_mutate_frontiers', s5_readonly),
    ],
}
