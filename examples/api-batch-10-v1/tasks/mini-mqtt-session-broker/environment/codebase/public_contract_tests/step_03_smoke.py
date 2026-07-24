#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mqtt_session_broker import parse_mqtt_events, replay_mqtt_events

events = parse_mqtt_events(json.dumps([
    {'seq': 1, 'action': 'connect', 'client_id': 'sub', 'clean_start': False},
    {'seq': 2, 'action': 'subscribe', 'client_id': 'sub', 'filter': 'devices/#', 'subscription_id': 'all', 'qos': 1},
    {'seq': 3, 'action': 'publish', 'topic': 'devices/a', 'payload': 'on', 'qos': 1, 'message_id': 'm1'},
    {'seq': 4, 'action': 'acknowledge', 'client_id': 'sub', 'ack_id': 'm1'},
    {'seq': 5, 'action': 'publish', 'topic': 'devices/retained', 'payload': 'r', 'retain': True, 'message_id': 'r1'}
]))
state = replay_mqtt_events(events)
assert any(delivery.message_id == 'm1' and delivery.status == 'acked' for delivery in state.deliveries)
assert 'devices/retained' in state.retained
print('step_03_smoke ok')
