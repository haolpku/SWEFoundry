from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    code: str


def _workspace() -> Path:
    return Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()


def _tests_dir() -> Path:
    return Path(os.environ.get('TDF_TESTS_DIR', Path.cwd())).resolve()


def _reward_dir() -> Path:
    return Path(os.environ.get('TDF_REWARD_DIR', _workspace() / 'reward')).resolve()


def _case_source(codebase: Path, code: str) -> str:
    return 'import sys\nsys.dont_write_bytecode=True\nsys.path.insert(0, ' + repr(str(codebase)) + ')\n' + code


def run_python_case(name: str, code: str, workspace: Path) -> dict:
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    codebase = workspace / 'environment' / 'codebase'
    proc = subprocess.run([sys.executable, '-I', '-c', _case_source(codebase, code)], cwd=str(workspace), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {'name': name, 'passed': proc.returncode == 0, 'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}


def step_checks(step: int) -> list[Check]:
    C = Check
    if step == 1:
        return [
            C('folded_summary_parses', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:fold','DTSTART:20250101T090000','DTEND:20250101T100000','SUMMARY:Alpha',' beta','SEQUENCE:1','STATUS:CONFIRMED','END:VEVENT','END:VCALENDAR',''])
events = parse_icalendar(text)
assert len(events) == 1
assert events[0].summary == 'Alphabeta'
'''),
            C('missing_uid_raises', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','DTSTART:20250101T090000','END:VEVENT','END:VCALENDAR',''])
try:
    parse_icalendar(text)
except Exception:
    pass
else:
    raise AssertionError('missing UID did not raise')
'''),
            C('parameter_parsing_preserves_values', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:param','DTSTART;TZID=Europe/Paris;VALUE=DATE:20250101','DTEND:20250102','END:VEVENT','END:VCALENDAR',''])
e = parse_icalendar(text)[0]
assert e.parameters['TZID'] == ('Europe/Paris',)
assert e.parameters['VALUE'] == ('DATE',)
'''),
            C('canonical_uid_and_recurrence_ordering', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:b','DTSTART:20250102T090000','END:VEVENT','BEGIN:VEVENT','UID:a','RECURRENCE-ID:20250103T090000','DTSTART:20250103T090000','END:VEVENT','BEGIN:VEVENT','UID:a','DTSTART:20250101T090000','END:VEVENT','END:VCALENDAR',''])
events = parse_icalendar(text)
assert [(e.uid, e.recurrence_id) for e in events] == [('a',''),('a','20250103T090000'),('b','')]
'''),
            C('rrule_sequence_status_fields', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:r','DTSTART:20250101T090000','RRULE:FREQ=daily;COUNT=2','SEQUENCE:7','STATUS:cancelled','END:VEVENT','END:VCALENDAR',''])
e = parse_icalendar(text)[0]
assert e.rrule == {'FREQ':'DAILY','COUNT':'2'}
assert e.sequence == 7
assert e.status == 'CANCELLED'
'''),
            C('exdate_values_are_canonical_and_sorted', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:x','DTSTART:20250101T090000','EXDATE:20250103T090000Z,20250102T090000','END:VEVENT','END:VCALENDAR',''])
e = parse_icalendar(text)[0]
assert e.exdates == ('20250102T090000','20250103T090000')
'''),
            C('unterminated_event_raises', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:u','DTSTART:20250101T090000','END:VCALENDAR',''])
try:
    parse_icalendar(text)
except Exception:
    pass
else:
    raise AssertionError('unterminated VEVENT did not raise')
'''),
            C('read_only_state_event_records', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:ro','DTSTART:20250101T090000','EXDATE:20250102T090000','END:VEVENT','END:VCALENDAR',''])
e = parse_icalendar(text)[0]
assert isinstance(e.exdates, tuple)
try:
    e.uid = 'mutated'
except Exception:
    pass
else:
    raise AssertionError('IcalEvent must be immutable')
'''),
        ]
    if step == 2:
        return [
            C('daily_count_expanded', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='d', dtstart='20250101T090000', dtend='20250101T100000', summary='Daily', rrule={'FREQ':'DAILY','COUNT':'3'})
occ = expand_ical_recurrences([e], '20250101T000000', '20250105T000000')
assert [o.start for o in occ] == ['20250101T090000','20250102T090000','20250103T090000']
assert [o.end for o in occ] == ['20250101T100000','20250102T100000','20250103T100000']
'''),
            C('until_is_inclusive', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='u', dtstart='20250101T090000', dtend='20250101T100000', rrule={'FREQ':'DAILY','UNTIL':'20250103T090000'})
occ = expand_ical_recurrences([e], '20250101T000000', '20250104T000000')
assert [o.start for o in occ] == ['20250101T090000','20250102T090000','20250103T090000']
'''),
            C('weekly_interval_handled', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='w', dtstart='20250101T090000', dtend='20250101T093000', rrule={'FREQ':'WEEKLY','INTERVAL':'2','COUNT':'3'})
occ = expand_ical_recurrences([e], '20250101T000000', '20250201T000000')
assert [o.start for o in occ] == ['20250101T090000','20250115T090000','20250129T090000']
'''),
            C('exdate_removes_occurrence', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='x', dtstart='20250101T090000', dtend='20250101T100000', rrule={'FREQ':'DAILY','COUNT':'3'}, exdates=('20250102T090000',))
occ = expand_ical_recurrences([e], '20250101T000000', '20250105T000000')
assert [o.start for o in occ] == ['20250101T090000','20250103T090000']
'''),
            C('window_start_inclusive_end_exclusive', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='b', dtstart='20250101T090000', dtend='20250101T100000', rrule={'FREQ':'DAILY','COUNT':'3'})
occ = expand_ical_recurrences([e], '20250102T090000', '20250103T090000')
assert [o.start for o in occ] == ['20250102T090000']
'''),
            C('cancelled_event_skipped', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='c', dtstart='20250101T090000', dtend='20250101T100000', status='CANCELLED', rrule={'FREQ':'DAILY','COUNT':'2'})
assert expand_ical_recurrences([e], '20250101T000000', '20250103T000000') == []
'''),
            C('unsupported_frequency_raises', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='m', dtstart='20250101T090000', rrule={'FREQ':'MONTHLY','COUNT':'2'})
try:
    expand_ical_recurrences([e], '20250101T000000', '20250103T000000')
except Exception:
    pass
else:
    raise AssertionError('unsupported FREQ did not raise')
'''),
            C('read_only_state_inputs_unmodified', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='ro', dtstart='20250101T090000', dtend='20250101T100000', rrule={'FREQ':'DAILY','COUNT':'1'})
events = [e]
before = repr(events)
occ = expand_ical_recurrences(events, '20250101T000000', '20250102T000000')
assert repr(events) == before
try:
    occ[0].start = 'mutated'
except Exception:
    pass
else:
    raise AssertionError('IcalOccurrence must be immutable')
'''),
        ]
    if step == 3:
        return [
            C('higher_sequence_update_wins', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='u', dtstart='20250101T090000', summary='old', sequence=1)]
newer = IcalEvent(uid='u', dtstart='20250101T090000', summary='new', sequence=2)
result = apply_ical_sync(base, [IcalSyncChange(action='UPDATE', event=newer)])
assert [(e.uid, e.summary, e.sequence) for e in result] == [('u','new',2)]
'''),
            C('older_update_is_ignored', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='u', dtstart='20250101T090000', summary='new', sequence=5)]
old = IcalEvent(uid='u', dtstart='20250101T090000', summary='old', sequence=4)
result = apply_ical_sync(base, [IcalSyncChange(action='UPDATE', event=old)])
assert [(e.summary, e.sequence) for e in result] == [('new',5)]
'''),
            C('delete_tombstone_hides_event', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='gone', dtstart='20250101T090000', sequence=1)]
result = apply_ical_sync(base, [IcalSyncChange(action='DELETE', uid='gone', sequence=2)])
assert result == []
'''),
            C('newer_tombstone_prevents_older_update', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='x', dtstart='20250101T090000', sequence=5, updated='20250105T000000', status='CANCELLED')]
old = IcalEvent(uid='x', dtstart='20250101T090000', summary='resurrect', sequence=4, updated='20250104T000000')
result = apply_ical_sync(base, [IcalSyncChange(action='UPDATE', event=old)])
assert result == []
'''),
            C('change_ordering_independence', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = []
a = IcalEvent(uid='a', dtstart='20250101T090000', sequence=1)
b = IcalEvent(uid='b', dtstart='20250101T090000', sequence=1)
left = apply_ical_sync(base, [IcalSyncChange(action='CREATE', event=b), IcalSyncChange(action='CREATE', event=a)])
right = apply_ical_sync(base, [IcalSyncChange(action='CREATE', event=a), IcalSyncChange(action='CREATE', event=b)])
assert [(e.uid, e.sequence) for e in left] == [(e.uid, e.sequence) for e in right] == [('a',1),('b',1)]
'''),
            C('recurrence_instance_isolated', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='r', recurrence_id='one', dtstart='20250101T090000', sequence=1), IcalEvent(uid='r', recurrence_id='two', dtstart='20250102T090000', sequence=1)]
result = apply_ical_sync(base, [IcalSyncChange(action='DELETE', uid='r', recurrence_id='one', sequence=2)])
assert [(e.uid, e.recurrence_id) for e in result] == [('r','two')]
'''),
            C('sorted_by_uid_output', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
changes = [IcalSyncChange(action='CREATE', event=IcalEvent(uid='z', dtstart='20250101T090000')), IcalSyncChange(action='CREATE', event=IcalEvent(uid='a', dtstart='20250101T090000'))]
result = apply_ical_sync([], changes)
assert [e.uid for e in result] == ['a','z']
'''),
            C('read_only_state_inputs_unmodified', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='ro', dtstart='20250101T090000', sequence=1)]
changes = [IcalSyncChange(action='DELETE', uid='ro', sequence=2)]
before = (repr(base), repr(changes))
apply_ical_sync(base, changes)
assert before == (repr(base), repr(changes))
'''),
        ]
    if step == 4:
        return [
            C('sequence_breaks_conflict', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
low = IcalEvent(uid='c', dtstart='20250101T090000', summary='low', sequence=1)
high = IcalEvent(uid='c', dtstart='20250101T090000', summary='high', sequence=2)
d = resolve_ical_conflicts([low, high])
assert len(d) == 1 and d[0].winner.summary == 'high'
'''),
            C('updated_breaks_equal_sequence', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
old = IcalEvent(uid='u', dtstart='20250101T090000', summary='old', sequence=3, updated='20250101T000000')
new = IcalEvent(uid='u', dtstart='20250101T090000', summary='new', sequence=3, updated='20250102T000000')
assert resolve_ical_conflicts([old, new])[0].winner.summary == 'new'
'''),
            C('tombstone_wins_on_newer_update', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
live = IcalEvent(uid='d', dtstart='20250101T090000', sequence=5, updated='20250101T000000')
tomb = IcalEvent(uid='d', dtstart='20250101T090000', sequence=5, updated='20250102T000000', status='CANCELLED')
assert resolve_ical_conflicts([live, tomb])[0].winner.status == 'CANCELLED'
'''),
            C('tie_break_deterministic_not_input_order', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
a = IcalEvent(uid='tie', dtstart='20250101T090000', summary='Alpha', sequence=7, updated='20250101T000000')
z = IcalEvent(uid='tie', dtstart='20250101T090000', summary='Zulu', sequence=7, updated='20250101T000000')
assert resolve_ical_conflicts([a, z])[0].winner.summary == 'Zulu'
assert resolve_ical_conflicts([z, a])[0].winner.summary == 'Zulu'
'''),
            C('uid_recurrence_grouping', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
a1 = IcalEvent(uid='r', recurrence_id='one', dtstart='20250101T090000', sequence=1)
a2 = IcalEvent(uid='r', recurrence_id='one', dtstart='20250101T090000', sequence=2)
b1 = IcalEvent(uid='r', recurrence_id='two', dtstart='20250102T090000', sequence=1)
b2 = IcalEvent(uid='r', recurrence_id='two', dtstart='20250102T090000', sequence=2)
d = resolve_ical_conflicts([b1, a1, b2, a2])
assert [(x.uid, x.recurrence_id, x.winner.sequence) for x in d] == [('r','one',2),('r','two',2)]
'''),
            C('stable_reason_contains_fields', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
x = IcalEvent(uid='why', dtstart='20250101T090000', sequence=1, updated='20250101T000000')
y = IcalEvent(uid='why', dtstart='20250101T090000', sequence=2, updated='20250102T000000')
reason = resolve_ical_conflicts([x, y])[0].reason
assert 'sequence=2' in reason and 'updated=20250102T000000' in reason and 'uid=why' in reason and 'recurrence_id=<master>' in reason
'''),
            C('no_decision_for_singleton', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
assert resolve_ical_conflicts([IcalEvent(uid='solo', dtstart='20250101T090000')]) == []
'''),
            C('read_only_state_candidates_unmodified', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
a = IcalEvent(uid='ro', dtstart='20250101T090000', sequence=1)
b = IcalEvent(uid='ro', dtstart='20250101T090000', sequence=2)
candidates = [a, b]
before = repr(candidates)
d = resolve_ical_conflicts(candidates)
assert repr(candidates) == before
try:
    d[0].winner.uid = 'mutated'
except Exception:
    pass
else:
    raise AssertionError('winner event must be immutable')
'''),
        ]
    if step == 5:
        return [
            C('text_snapshot_migrates_with_warning', '''from mini_ical_sync_engine import audit_ical_sync
snapshot = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:t','DTSTART:20250101T090000','DTEND:20250101T100000','SUMMARY:Text','END:VEVENT','END:VCALENDAR',''])
r = audit_ical_sync(snapshot, '', '20250101T000000', '20250102T000000')
assert r.snapshot_version == 2
assert r.warnings == ('migrated text snapshot to version 2',)
assert [e.uid for e in r.events] == ['t']
'''),
            C('json_v1_snapshot_migrates_and_sorts', '''import json
from mini_ical_sync_engine import audit_ical_sync
snapshot = json.dumps({'version':1,'events':[{'uid':'b','dtstart':'20250101T090000'},{'uid':'a','dtstart':'20250101T090000'}]})
r = audit_ical_sync(snapshot, '', '20250101T000000', '20250102T000000')
assert r.snapshot_version == 2
assert 'migrated snapshot version 1 to 2' in r.warnings
assert [e.uid for e in r.events] == ['a','b']
'''),
            C('conflict_resolution_precedes_expansion', '''import json
from mini_ical_sync_engine import audit_ical_sync
snapshot = json.dumps({'version':2,'events':[{'uid':'c','dtstart':'20250101T090000','dtend':'20250101T100000','summary':'Losing','sequence':1,'rrule':{'FREQ':'DAILY','COUNT':'3'}}]})
incoming = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:c','DTSTART:20250101T090000','DTEND:20250101T100000','SUMMARY:Winning','SEQUENCE:2','END:VEVENT','END:VCALENDAR',''])
r = audit_ical_sync(snapshot, incoming, '20250101T000000', '20250105T000000')
assert [e.summary for e in r.events] == ['Winning']
assert [o.summary for o in r.occurrences] == ['Winning']
assert len(r.conflicts) == 1
'''),
            C('tombstone_compaction_removes_occurrences', '''import json
from mini_ical_sync_engine import audit_ical_sync
snapshot = json.dumps({'version':2,'events':[{'uid':'dead','dtstart':'20250101T090000','dtend':'20250101T100000','summary':'Live','sequence':1,'rrule':{'FREQ':'DAILY','COUNT':'2'}}]})
incoming = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:dead','DTSTART:20250101T090000','DTEND:20250101T100000','SUMMARY:Deleted','SEQUENCE:2','STATUS:CANCELLED','END:VEVENT','END:VCALENDAR',''])
r = audit_ical_sync(snapshot, incoming, '20250101T000000', '20250105T000000')
assert r.events == () and r.occurrences == ()
assert r.conflicts and r.conflicts[0].winner.status == 'CANCELLED'
'''),
            C('regression_step1_folded_parse', '''from mini_ical_sync_engine import parse_icalendar
text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:f','DTSTART:20250101T090000','SUMMARY:Fold',' ed','END:VEVENT','END:VCALENDAR',''])
assert parse_icalendar(text)[0].summary == 'Folded'
'''),
            C('regression_step2_until_inclusive', '''from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences
e = IcalEvent(uid='u', dtstart='20250101T090000', rrule={'FREQ':'DAILY','UNTIL':'20250102T090000'})
assert [o.start for o in expand_ical_recurrences([e], '20250101T000000', '20250103T000000')] == ['20250101T090000','20250102T090000']
'''),
            C('regression_step3_tombstone_precedence', '''from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync
base = [IcalEvent(uid='x', dtstart='20250101T090000', sequence=5, status='CANCELLED', updated='20250105T000000')]
old = IcalEvent(uid='x', dtstart='20250101T090000', sequence=4, updated='20250104T000000')
assert apply_ical_sync(base, [IcalSyncChange(action='UPDATE', event=old)]) == []
'''),
            C('regression_step4_tie_break', '''from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts
a = IcalEvent(uid='tie', dtstart='20250101T090000', summary='Alpha', sequence=1)
z = IcalEvent(uid='tie', dtstart='20250101T090000', summary='Zulu', sequence=1)
assert resolve_ical_conflicts([a, z])[0].winner.summary == 'Zulu'
'''),
            C('read_only_state_audit_report_records', '''from mini_ical_sync_engine import audit_ical_sync
r = audit_ical_sync('', '', '20250101T000000', '20250102T000000')
assert r.events == () and r.occurrences == ()
try:
    r.snapshot_version = 99
except Exception:
    pass
else:
    raise AssertionError('IcalSyncAuditReport must be immutable')
'''),
        ]
    raise ValueError('unknown step')


def write_outputs(step: int, results: list[dict]) -> int:
    reward_dir = _reward_dir()
    reward_dir.mkdir(parents=True, exist_ok=True)
    total = len(results)
    passed = sum(1 for item in results if item['passed'])
    correctness = 1.0 if passed == total else passed / total
    release_pass = 1 if correctness == 1.0 else 0
    reward = {'correctness': correctness, 'code_quality': correctness, 'reasoning': correctness, 'efficiency': correctness, 'weighted_total': correctness, 'release_pass': release_pass}
    evidence = {'step': step, 'tests_dir': str(_tests_dir()), 'checks': results}
    ctrf_tests = [{'name': r['name'], 'status': 'passed' if r['passed'] else 'failed'} for r in results]
    ctrf = {'results': {'summary': {'tests': total, 'passed': passed, 'failed': total - passed}, 'tests': ctrf_tests}}
    (reward_dir / 'reward.json').write_text(json.dumps(reward, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (reward_dir / 'reward.txt').write_text(str(reward['weighted_total']) + '\n', encoding='utf-8')
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if release_pass == 1 else 1


def run_verification(step: int) -> int:
    os.environ.pop('PYTHONPATH', None)
    os.environ.pop('PYTHONHOME', None)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    workspace = _workspace()
    results = [run_python_case(check.name, check.code, workspace) for check in step_checks(step)]
    return write_outputs(step, results)
