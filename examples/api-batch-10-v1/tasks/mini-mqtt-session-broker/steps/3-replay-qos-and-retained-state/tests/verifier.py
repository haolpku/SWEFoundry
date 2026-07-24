#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'verifier'))
from common import Check, run_json, run_step


def qos1_awaits_ack(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub', 'clean_start': False},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'topic/#', 'subscription_id': 's', 'qos': 1},
    {'seq': 3, 'action': 'publish', 'topic': 'topic/a', 'payload': 'x', 'qos': 1, 'message_id': 'm1'}
]))
state = replay_mqtt_events(events)
print(json.dumps([(d.client_id, d.message_id, d.status, d.qos) for d in state.deliveries]))
''')
    assert data == [['sub', 'm1', 'pending', 1]]


def qos1_ack_changes_status(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub', 'clean_start': False},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'topic/#', 'subscription_id': 's', 'qos': 1},
    {'seq': 3, 'action': 'publish', 'topic': 'topic/a', 'payload': 'x', 'qos': 1, 'message_id': 'm1'},
    {'seq': 4, 'action': 'acknowledge', 'client_id': 'sub', 'ack_id': 'm1'}
]))
state = replay_mqtt_events(events)
print(json.dumps([(d.message_id, d.status) for d in state.deliveries]))
''')
    assert data == [['m1', 'acked']]


def qos1_duplicate_offline_suppression(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub', 'clean_start': False},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'topic/#', 'subscription_id': 's', 'qos': 1, 'durable': True},
    {'seq': 3, 'action': 'disconnect', 'client_id': 'sub'},
    {'seq': 4, 'action': 'publish', 'topic': 'topic/a', 'payload': 'x', 'qos': 1, 'message_id': 'same'},
    {'seq': 5, 'action': 'publish', 'topic': 'topic/a', 'payload': 'x', 'qos': 1, 'message_id': 'same'}
]))
state = replay_mqtt_events(events)
queue = state.sessions['sub'].queue
print(json.dumps([(d.message_id, d.seq, d.status) for d in queue]))
''')
    assert data == [['same', 4, 'pending']]


def qos0_immediate_delivery(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub'},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'a/b', 'subscription_id': 's', 'qos': 0},
    {'seq': 3, 'action': 'publish', 'topic': 'a/b', 'payload': 'x', 'qos': 0, 'message_id': 'm0'}
]))
state = replay_mqtt_events(events)
print(json.dumps([(d.message_id, d.status, d.qos) for d in state.deliveries]))
''')
    assert data == [['m0', 'delivered', 0]]


def retained_message_delivered_on_subscribe(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'publish', 'topic': 'retained/a', 'payload': 'r', 'retain': True, 'message_id': 'r1'},
    {'seq': 2, 'action': 'connect', 'client_id': 'sub'},
    {'seq': 3, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'retained/#', 'subscription_id': 's', 'qos': 1}
]))
state = replay_mqtt_events(events)
print(json.dumps({'retained': sorted(state.retained), 'deliveries': [(d.client_id, d.message_id, d.retained, d.payload) for d in state.deliveries]}, sort_keys=True))
''')
    assert data == {'retained': ['retained/a'], 'deliveries': [['sub', 'r1', True, 'r']]}


def retained_delete_tombstone(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'publish', 'topic': 'retained/a', 'payload': 'r', 'retain': True, 'message_id': 'r1'},
    {'seq': 2, 'action': 'publish', 'topic': 'retained/a', 'payload': '', 'retain': True, 'message_id': 'r2'}
]))
state = replay_mqtt_events(events)
print(json.dumps({'retained': sorted(state.retained), 'tombstones': list(state.retained_tombstones)}, sort_keys=True))
''')
    assert data == {'retained': [], 'tombstones': ['retained/a']}


def durable_offline_queue_replayed_on_connect(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub', 'clean_start': False},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'offline/#', 'subscription_id': 's', 'qos': 1, 'durable': True},
    {'seq': 3, 'action': 'disconnect', 'client_id': 'sub'},
    {'seq': 4, 'action': 'publish', 'topic': 'offline/a', 'payload': 'queued', 'qos': 1, 'message_id': 'q1'},
    {'seq': 5, 'action': 'connect', 'client_id': 'sub', 'clean_start': False}
]))
state = replay_mqtt_events(events)
print(json.dumps({'deliveries': [(d.client_id, d.message_id, d.payload) for d in state.deliveries], 'queue': len(state.sessions['sub'].queue)}, sort_keys=True))
''')
    assert data == {'deliveries': [['sub', 'q1', 'queued']], 'queue': 0}


def read_only_broker_state_check(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'sub'}]))
state = replay_mqtt_events(events)
try:
    state.sessions['other'] = None
    mapping_read_only = False
except Exception:
    mapping_read_only = True
try:
    state.deliveries.append(None)
    deliveries_tuple = False
except Exception:
    deliveries_tuple = True
print(json.dumps({'mapping_read_only': mapping_read_only, 'deliveries_tuple': deliveries_tuple}, sort_keys=True))
''')
    assert data == {'mapping_read_only': True, 'deliveries_tuple': True}


CHECKS = [
    Check('qos1_awaits_ack', qos1_awaits_ack),
    Check('qos1_ack_changes_status', qos1_ack_changes_status),
    Check('qos1_duplicate_offline_suppression', qos1_duplicate_offline_suppression),
    Check('qos0_immediate_delivery', qos0_immediate_delivery),
    Check('retained_message_delivered_on_subscribe', retained_message_delivered_on_subscribe),
    Check('retained_delete_tombstone', retained_delete_tombstone),
    Check('durable_offline_queue_replayed_on_connect', durable_offline_queue_replayed_on_connect),
    Check('read_only_broker_state_check', read_only_broker_state_check),
]

if __name__ == '__main__':
    raise SystemExit(run_step('step-3', CHECKS))
