#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'verifier'))
from common import Check, run_json, run_step


def unsupported_qos_advice(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'publish', 'topic': 'bad/qos', 'payload': 'x', 'qos': 2}]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target, a.seq) for a in advice]))
''')
    assert ['unsupported-qos', 'bad/qos', 1] in data


def explicit_expire_stale_session(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'old'}, {'seq': 2, 'action': 'expire', 'client_id': 'old'}]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target) for a in advice]))
''')
    assert ['stale-session', 'old'] in data


def no_live_time_expiry_without_expire(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'idle', 'clean_start': False}, {'seq': 2, 'action': 'disconnect', 'client_id': 'idle'}]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target) for a in advice]))
''')
    assert ['stale-session', 'idle'] not in data


def retained_tombstone_advice(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'publish', 'topic': 'retain/x', 'payload': 'v', 'retain': True}, {'seq': 2, 'action': 'publish', 'topic': 'retain/x', 'payload': '', 'retain': True}]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target) for a in advice]))
''')
    assert ['retained-tombstone', 'retain/x'] in data


def compaction_advice_for_acked_qos1(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub'},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'a/#', 'subscription_id': 's', 'qos': 1},
    {'seq': 3, 'action': 'publish', 'topic': 'a/b', 'payload': 'x', 'qos': 1, 'message_id': 'm1'},
    {'seq': 4, 'action': 'acknowledge', 'client_id': 'sub', 'ack_id': 'm1'}
]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target, a.seq) for a in advice]))
''')
    assert ['compact-session', 'sub', 3] in data


def advice_deduplicated(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'dup'}, {'seq': 2, 'action': 'expire', 'client_id': 'dup'}, {'seq': 3, 'action': 'expire', 'client_id': 'dup'}]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target, a.detail) for a in advice]))
''')
    stale = [item for item in data if item[0] == 'stale-session' and item[1] == 'dup']
    assert len(stale) == 1


def stable_advice_ordering(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([
    {'seq': 5, 'action': 'publish', 'topic': 'z/qos', 'payload': 'x', 'qos': 2},
    {'seq': 1, 'action': 'publish', 'topic': 'a/ret', 'payload': 'x', 'retain': True},
    {'seq': 2, 'action': 'publish', 'topic': 'a/ret', 'payload': '', 'retain': True},
    {'seq': 3, 'action': 'connect', 'client_id': 'old'},
    {'seq': 4, 'action': 'expire', 'client_id': 'old'}
]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
print(json.dumps([(a.category, a.target, a.detail, a.seq) for a in advice]))
''')
    assert data == sorted(data)


def read_only_planning_state_check(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events
events = parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'ro'}]))
state = replay_mqtt_events(events)
before = (sorted(state.sessions), len(state.deliveries), sorted(state.retained))
plan_mqtt_migration(state)
after = (sorted(state.sessions), len(state.deliveries), sorted(state.retained))
try:
    state.sessions['x'] = None
    immutable = False
except Exception:
    immutable = True
print(json.dumps({'same': before == after, 'immutable': immutable}, sort_keys=True))
''')
    assert data == {'same': True, 'immutable': True}


CHECKS = [
    Check('unsupported_qos_advice', unsupported_qos_advice),
    Check('explicit_expire_stale_session', explicit_expire_stale_session),
    Check('no_live_time_expiry_without_expire', no_live_time_expiry_without_expire),
    Check('retained_tombstone_advice', retained_tombstone_advice),
    Check('compaction_advice_for_acked_qos1', compaction_advice_for_acked_qos1),
    Check('advice_deduplicated', advice_deduplicated),
    Check('stable_advice_ordering', stable_advice_ordering),
    Check('read_only_planning_state_check', read_only_planning_state_check),
]

if __name__ == '__main__':
    raise SystemExit(run_step('step-4', CHECKS))
