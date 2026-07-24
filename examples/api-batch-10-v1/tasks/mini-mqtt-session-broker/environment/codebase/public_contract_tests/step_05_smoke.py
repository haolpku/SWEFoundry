#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mqtt_session_broker import audit_mqtt_session

snapshot = json.dumps({'events': [
    {'seq': 1, 'action': 'publish', 'topic': 'sensors/room/temp', 'payload': '21C', 'retain': True, 'message_id': 'ret1'}
]})
journal = json.dumps({'events': [
    {'seq': 2, 'action': 'connect', 'client_id': 'client-A', 'clean_start': False},
    {'seq': 3, 'action': 'subscribe', 'client_id': 'client-A', 'filter': 'sensors/+/temp', 'subscription_id': 'temp', 'qos': 1}
]})
report = audit_mqtt_session(snapshot, journal)
assert report.to_dict()['event_count'] == 3
assert report.retained_topics == ('sensors/room/temp',)
assert any(delivery.retained and delivery.client_id == 'client-A' for delivery in report.deliveries)
print('step_05_smoke ok')
