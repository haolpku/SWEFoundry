#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mqtt_session_broker import parse_mqtt_events, plan_mqtt_migration, replay_mqtt_events

events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'client-A', 'clean_start': False},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'client-A', 'filter': 'ops/#', 'subscription_id': 'ops', 'qos': 1},
    {'seq': 3, 'action': 'publish', 'topic': 'ops/a', 'payload': 'x', 'qos': 1, 'message_id': 'm1'},
    {'seq': 4, 'action': 'acknowledge', 'client_id': 'client-A', 'ack_id': 'm1'},
    {'seq': 5, 'action': 'publish', 'topic': 'ops/deprecated', 'payload': '', 'retain': True, 'qos': 2},
    {'seq': 6, 'action': 'expire', 'client_id': 'client-A'}
]))
advice = plan_mqtt_migration(replay_mqtt_events(events))
categories = {item.category for item in advice}
assert {'unsupported-qos', 'compact-session', 'retained-tombstone', 'stale-session'} <= categories
print('step_04_smoke ok')
