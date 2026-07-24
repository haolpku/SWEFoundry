#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'verifier'))
from common import Check, expect_error, run_json, run_step


def sorted_by_explicit_sequence(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 3, 'action': 'disconnect', 'client_id': 'client-A'},
    {'seq': 1, 'action': 'connect', 'client_id': 'client-A'},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'client-A', 'filter': 'a/b', 'sub_id': 'sub'}
]))
print(json.dumps([event.seq for event in events]))
''')
    assert data == [1, 2, 3]


def duplicate_sequence_rejected(workspace: Path) -> None:
    expect_error(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'a'}, {'seq': 1, 'action': 'disconnect', 'client_id': 'a'}]))
''')


def invalid_client_identifier_rejected(workspace: Path) -> None:
    expect_error(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'bad client id with spaces'}]))
''')


def publish_topic_wildcard_rejected(workspace: Path) -> None:
    expect_error(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'publish', 'topic': 'a/+/c', 'payload': 'x'}]))
''')


def malformed_subscribe_filter_rejected(workspace: Path) -> None:
    expect_error(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'subscribe', 'client_id': 'client-A', 'filter': 'a/#/c'}]))
''')


def empty_topic_level_rejected(workspace: Path) -> None:
    expect_error(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'publish', 'topic': 'a//c', 'payload': 'x'}]))
''')


def action_and_alias_fields_preserved(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 2, 'action': 'acknowledge', 'client_id': 'client-A', 'message_id': 'm1'},
    {'seq': 1, 'action': 'subscribe', 'client_id': 'client-A', 'topic_filter': 'devices/+', 'sub_id': 'sub-alias', 'qos': 1, 'durable': False}
]))
print(json.dumps({'filter': events[0].topic_filter, 'sub': events[0].subscription_id, 'ack': events[1].ack_id, 'durable': events[0].durable}, sort_keys=True))
''')
    assert data == {'filter': 'devices/+', 'sub': 'sub-alias', 'ack': 'm1', 'durable': False}


def read_only_event_state_check(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events
event = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'client-A'}]))[0]
try:
    event.seq = 99
    frozen = False
except Exception:
    frozen = event.seq == 1
print(json.dumps({'frozen': frozen, 'seq': event.seq}, sort_keys=True))
''')
    assert data == {'frozen': True, 'seq': 1}


CHECKS = [
    Check('sorted_by_explicit_sequence', sorted_by_explicit_sequence),
    Check('duplicate_sequence_rejected', duplicate_sequence_rejected),
    Check('invalid_client_identifier_rejected', invalid_client_identifier_rejected),
    Check('publish_topic_wildcard_rejected', publish_topic_wildcard_rejected),
    Check('malformed_subscribe_filter_rejected', malformed_subscribe_filter_rejected),
    Check('empty_topic_level_rejected', empty_topic_level_rejected),
    Check('action_and_alias_fields_preserved', action_and_alias_fields_preserved),
    Check('read_only_event_state_check', read_only_event_state_check),
]

if __name__ == '__main__':
    raise SystemExit(run_step('step-1', CHECKS))
