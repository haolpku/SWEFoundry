#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'verifier'))
from common import Check, expect_error, run_json, run_step


def fresh_journal_audit_counts(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
journal = json.dumps({'events': [
    {'seq': 1, 'action': 'connect', 'client_id': 'client-A'},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'client-A', 'filter': 'a/#', 'subscription_id': 's'},
    {'seq': 3, 'action': 'publish', 'topic': 'a/b', 'payload': 'x', 'message_id': 'm'}
]})
report = audit_mqtt_session(None, journal)
print(json.dumps({'dict': report.to_dict()['event_count'], 'sessions': list(report.sessions), 'deliveries': len(report.deliveries)}, sort_keys=True))
''')
    assert data == {'dict': 3, 'sessions': ['client-A'], 'deliveries': 1}


def snapshot_journal_recovery_retains_messages(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
snapshot = json.dumps({'events': [{'seq': 1, 'action': 'publish', 'topic': 'sensors/room/temp', 'payload': '21C', 'retain': True, 'message_id': 'ret1'}]})
journal = json.dumps({'events': [
    {'seq': 2, 'action': 'connect', 'client_id': 'mobile', 'clean_start': False},
    {'seq': 3, 'action': 'subscribe', 'client_id': 'mobile', 'filter': 'sensors/+/temp', 'subscription_id': 'temp', 'qos': 1}
]})
report = audit_mqtt_session(snapshot, journal)
print(json.dumps({'retained_topics': list(report.retained_topics), 'retained_deliveries': [(d.client_id, d.topic, d.payload, d.retained) for d in report.deliveries if d.retained]}, sort_keys=True))
''')
    assert data == {'retained_topics': ['sensors/room/temp'], 'retained_deliveries': [['mobile', 'sensors/room/temp', '21C', True]]}


def journal_replay_idempotent_ordering(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
journal = json.dumps({'events': [
    {'seq': 3, 'action': 'publish', 'topic': 'a/b', 'payload': 'x', 'message_id': 'm'},
    {'seq': 1, 'action': 'connect', 'client_id': 'c'},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'c', 'filter': 'a/#', 'subscription_id': 's'}
]})
first = audit_mqtt_session(None, journal).to_dict()
second = audit_mqtt_session(None, journal).to_dict()
print(json.dumps({'same': first == second, 'seqs': [d['seq'] for d in first['deliveries']]}, sort_keys=True))
''')
    assert data == {'same': True, 'seqs': [3]}


def parse_regression_sequence_sort_and_validation(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
journal = json.dumps({'events': [{'seq': 2, 'action': 'disconnect', 'client_id': 'c'}, {'seq': 1, 'action': 'connect', 'client_id': 'c'}]})
report = audit_mqtt_session(None, journal)
print(json.dumps([event.seq for event in report.events]))
''')
    assert data == [1, 2]
    expect_error(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
audit_mqtt_session(None, json.dumps({'events': [{'seq': 1, 'action': 'connect', 'client_id': 'bad client'}]}))
''')


def match_regression_wildcard_integrated(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
journal = json.dumps({'events': [
    {'seq': 1, 'action': 'publish', 'topic': 'fleet/truck/position', 'payload': 'p', 'retain': True, 'message_id': 'ret'},
    {'seq': 2, 'action': 'connect', 'client_id': 'tracker'},
    {'seq': 3, 'action': 'subscribe', 'client_id': 'tracker', 'filter': 'fleet/+/position', 'subscription_id': 'pos'}
]})
report = audit_mqtt_session(None, journal)
print(json.dumps([(d.client_id, d.topic, d.retained) for d in report.deliveries]))
''')
    assert data == [['tracker', 'fleet/truck/position', True]]


def replay_regression_qos_ack(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
journal = json.dumps({'events': [
    {'seq': 1, 'action': 'connect', 'client_id': 'sub'},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'q/#', 'subscription_id': 'q', 'qos': 1},
    {'seq': 3, 'action': 'publish', 'topic': 'q/a', 'payload': 'x', 'qos': 1, 'message_id': 'm'},
    {'seq': 4, 'action': 'acknowledge', 'client_id': 'sub', 'ack_id': 'm'}
]})
report = audit_mqtt_session(None, journal)
print(json.dumps([(d.message_id, d.status) for d in report.deliveries]))
''')
    assert data == [['m', 'acked']]


def migration_regression_advice(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
journal = json.dumps({'events': [{'seq': 1, 'action': 'publish', 'topic': 'bad/qos', 'payload': 'x', 'qos': 2}, {'seq': 2, 'action': 'expire', 'client_id': 'old'}]})
report = audit_mqtt_session(None, journal)
print(json.dumps(sorted((a.category, a.target) for a in report.advice)))
''')
    assert ['unsupported-qos', 'bad/qos'] in data
    assert ['stale-session', 'old'] in data


def critical_duplicate_sequence_rejected_across_snapshot_journal(workspace: Path) -> None:
    expect_error(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
snapshot = json.dumps({'events': [{'seq': 1, 'action': 'connect', 'client_id': 'c'}]})
journal = json.dumps({'events': [{'seq': 1, 'action': 'disconnect', 'client_id': 'c'}]})
audit_mqtt_session(snapshot, journal)
''')


def read_only_audit_report_state_check(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import audit_mqtt_session
report = audit_mqtt_session(None, json.dumps({'events': [{'seq': 1, 'action': 'connect', 'client_id': 'ro'}]}))
try:
    report.events.append(None)
    events_tuple = False
except Exception:
    events_tuple = True
try:
    report.state.sessions['x'] = None
    sessions_read_only = False
except Exception:
    sessions_read_only = True
print(json.dumps({'events_tuple': events_tuple, 'sessions_read_only': sessions_read_only}, sort_keys=True))
''')
    assert data == {'events_tuple': True, 'sessions_read_only': True}


CHECKS = [
    Check('fresh_journal_audit_counts', fresh_journal_audit_counts),
    Check('snapshot_journal_recovery_retains_messages', snapshot_journal_recovery_retains_messages),
    Check('journal_replay_idempotent_ordering', journal_replay_idempotent_ordering),
    Check('parse_regression_sequence_sort_and_validation', parse_regression_sequence_sort_and_validation),
    Check('match_regression_wildcard_integrated', match_regression_wildcard_integrated),
    Check('replay_regression_qos_ack', replay_regression_qos_ack),
    Check('migration_regression_advice', migration_regression_advice),
    Check('critical_duplicate_sequence_rejected_across_snapshot_journal', critical_duplicate_sequence_rejected_across_snapshot_journal),
    Check('read_only_audit_report_state_check', read_only_audit_report_state_check),
]

if __name__ == '__main__':
    raise SystemExit(run_step('step-5', CHECKS))
