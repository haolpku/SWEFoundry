from __future__ import annotations

import json
from typing import Any

from .exceptions import MqttParseError, MqttValidationError
from .models import MqttAuditReport
from .parser import parse_mqtt_events
from .replay import replay_mqtt_events
from .migration import plan_mqtt_migration


def _snapshot_events(snapshot: str | None) -> list[Any]:
    if snapshot is None or snapshot == "":
        return []
    try:
        data = json.loads(snapshot)
    except json.JSONDecodeError as exc:
        raise MqttParseError(str(exc)) from exc
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "events" in data and isinstance(data["events"], list):
            return data["events"]
        if "snapshot_events" in data and isinstance(data["snapshot_events"], list):
            return data["snapshot_events"]
    raise MqttValidationError("snapshot must contain an events list")


def _journal_events(journal: str) -> list[Any]:
    try:
        data = json.loads(journal)
    except json.JSONDecodeError as exc:
        raise MqttParseError(str(exc)) from exc
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "events" in data and isinstance(data["events"], list):
        return data["events"]
    raise MqttValidationError("journal must contain an events list")


def audit_mqtt_session(snapshot: str | None, journal: str) -> MqttAuditReport:
    combined = _snapshot_events(snapshot) + _journal_events(journal)
    canonical = json.dumps(combined, sort_keys=True, separators=(",", ":"))
    events = parse_mqtt_events(canonical)
    state = replay_mqtt_events(events)
    advice = tuple(plan_mqtt_migration(state))
    return MqttAuditReport(events=tuple(events), state=state, advice=advice, deliveries=state.deliveries, retained_topics=tuple(sorted(state.retained)), sessions=tuple(sorted(state.sessions)))
