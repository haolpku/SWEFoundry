from __future__ import annotations

from .models import BrokerState, MqttMigrationAdvice


def plan_mqtt_migration(state: BrokerState) -> list[MqttMigrationAdvice]:
    advice: set[tuple[str, str, str, int]] = set()
    for event in state.events:
        if event.qos not in (0, 1):
            target = event.client_id or event.topic or "broker"
            advice.add(("unsupported-qos", target, f"qos {event.qos} is not supported by the offline broker", event.seq))
    for client_id in state.expired_clients:
        advice.add(("stale-session", client_id, "session has an explicit expire event", 0))
    for topic in state.retained_tombstones:
        advice.add(("retained-tombstone", topic, "retained message was deleted by an empty retained publish", 0))
    for client_id, session in state.sessions.items():
        acked = [delivery for delivery in state.deliveries if delivery.client_id == client_id and delivery.status == "acked"]
        if acked:
            advice.add(("compact-session", client_id, f"{len(acked)} acknowledged qos1 deliveries can be compacted", min(d.seq for d in acked)))
        if session.expired:
            advice.add(("stale-session", client_id, "session has an explicit expire event", 0))
    return [MqttMigrationAdvice(category, target, detail, seq) for category, target, detail, seq in sorted(advice)]
