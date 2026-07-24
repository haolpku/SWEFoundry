#!/usr/bin/env python3
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'verifier'))
from common import Check, expect_error, run_json, run_step


def exact_filter_match(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
subs = [Subscription('c', 'exact', 'alerts/critical'), Subscription('c', 'other', 'alerts/info')]
print(json.dumps(match_mqtt_subscriptions(subs, 'alerts/critical')))
''')
    assert data == ['exact']


def single_level_wildcard_match(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
subs = [Subscription('c', 'room-temp', 'sensors/+/temp'), Subscription('c', 'room-humidity', 'sensors/+/humidity')]
print(json.dumps(match_mqtt_subscriptions(subs, 'sensors/kitchen/temp')))
''')
    assert data == ['room-temp']


def terminal_hash_wildcard_match(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
subs = [Subscription('c', 'all', 'factory/#'), Subscription('c', 'root', 'factory')]
print(json.dumps({'child': match_mqtt_subscriptions(subs, 'factory/line/a'), 'root': match_mqtt_subscriptions(subs, 'factory')}, sort_keys=True))
''')
    assert data == {'child': ['all'], 'root': ['all', 'root']}


def hash_not_partial_topic_level(workspace: Path) -> None:
    expect_error(workspace, '''
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
match_mqtt_subscriptions([Subscription('c', 'bad', 'sport/tennis#')], 'sport/tennis/ranking')
''')


def hash_must_be_terminal(workspace: Path) -> None:
    expect_error(workspace, '''
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
match_mqtt_subscriptions([Subscription('c', 'bad', 'sport/#/ranking')], 'sport/pro/ranking')
''')


def plus_whole_level_only(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
ok = match_mqtt_subscriptions([Subscription('c', 'plus', 'sport/+/ranking')], 'sport/pro/ranking')
print(json.dumps(ok))
''')
    assert data == ['plus']
    expect_error(workspace, '''
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
match_mqtt_subscriptions([Subscription('c', 'bad', 'sport/pro+/ranking')], 'sport/pro/ranking')
''')


def lexical_identifier_order(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
subs = [Subscription('c', 'zeta', 'a/#'), Subscription('c', 'alpha', 'a/b'), Subscription('c', 'middle', 'a/+')]
print(json.dumps(match_mqtt_subscriptions(subs, 'a/b')))
''')
    assert data == ['alpha', 'middle', 'zeta']


def invalid_topic_wildcard_rejected(workspace: Path) -> None:
    expect_error(workspace, '''
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
match_mqtt_subscriptions([Subscription('c', 'x', 'a/#')], 'a/+/b')
''')


def read_only_subscription_state_check(workspace: Path) -> None:
    data = run_json(workspace, '''
import json
from mqtt_session_broker import Subscription, match_mqtt_subscriptions
sub = Subscription('c', 'id', 'a/#', qos=1)
subs = [sub]
result = match_mqtt_subscriptions(subs, 'a/b')
try:
    sub.qos = 0
    frozen = False
except Exception:
    frozen = sub.qos == 1
print(json.dumps({'frozen': frozen, 'unchanged': [(s.identifier, s.topic_filter, s.qos) for s in subs], 'result': result}, sort_keys=True))
''')
    assert data == {'frozen': True, 'unchanged': [['id', 'a/#', 1]], 'result': ['id']}


CHECKS = [
    Check('exact_filter_match', exact_filter_match),
    Check('single_level_wildcard_match', single_level_wildcard_match),
    Check('terminal_hash_wildcard_match', terminal_hash_wildcard_match),
    Check('hash_not_partial_topic_level', hash_not_partial_topic_level),
    Check('hash_must_be_terminal', hash_must_be_terminal),
    Check('plus_whole_level_only', plus_whole_level_only),
    Check('lexical_identifier_order', lexical_identifier_order),
    Check('invalid_topic_wildcard_rejected', invalid_topic_wildcard_rejected),
    Check('read_only_subscription_state_check', read_only_subscription_state_check),
]

if __name__ == '__main__':
    raise SystemExit(run_step('step-2', CHECKS))
