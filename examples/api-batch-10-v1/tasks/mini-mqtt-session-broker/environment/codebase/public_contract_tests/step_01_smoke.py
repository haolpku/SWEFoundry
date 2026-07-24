#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mqtt_session_broker import MqttValidationError, parse_mqtt_events

payload = json.dumps([
    {'seq': 2, 'action': 'subscribe', 'client_id': 'client-A', 'filter': 'sensors/+/temp', 'sub_id': 'sub-temp', 'qos': 1},
    {'seq': 1, 'action': 'connect', 'client_id': 'client-A', 'clean_start': False},
    {'seq': 3, 'action': 'publish', 'topic': 'sensors/room/temp', 'payload': '21C', 'message_id': 'm1'}
])
events = parse_mqtt_events(payload)
assert [event.seq for event in events] == [1, 2, 3]
assert events[1].topic_filter == 'sensors/+/temp'
assert events[1].subscription_id == 'sub-temp'
try:
    parse_mqtt_events(json.dumps([{'seq': 1, 'action': 'connect', 'client_id': 'a'}, {'seq': 1, 'action': 'disconnect', 'client_id': 'a'}]))
except MqttValidationError:
    pass
else:
    raise AssertionError('duplicate sequence was accepted')
print('step_01_smoke ok')
