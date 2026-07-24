#!/usr/bin/env python3
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mqtt_session_broker import MqttValidationError, Subscription, match_mqtt_subscriptions

subs = [
    Subscription('client-A', 'b', 'sensors/+/temp'),
    Subscription('client-A', 'a', 'sensors/#'),
    Subscription('client-A', 'z', 'alerts/critical')
]
assert match_mqtt_subscriptions(subs, 'sensors/room/temp') == ['a', 'b']
assert match_mqtt_subscriptions(subs, 'alerts/critical') == ['z']
try:
    match_mqtt_subscriptions([Subscription('c', 'bad', 'sensors/#/temp')], 'sensors/x/temp')
except MqttValidationError:
    pass
else:
    raise AssertionError('non-terminal hash filter was accepted')
print('step_02_smoke ok')
