from __future__ import annotations

from .models import MqttAuditReport
from .parser import parse_mqtt_events
from .replay import replay_mqtt_events
from .migration import plan_mqtt_migration


def audit_mqtt_session(snapshot: str | None, journal: str) -> MqttAuditReport:
    events = parse_mqtt_events(journal)
    state = replay_mqtt_events(events)
    advice = tuple(plan_mqtt_migration(state))
    return MqttAuditReport(tuple(events), state, advice, state.deliveries, tuple(sorted(state.retained)), tuple(sorted(state.sessions)))
