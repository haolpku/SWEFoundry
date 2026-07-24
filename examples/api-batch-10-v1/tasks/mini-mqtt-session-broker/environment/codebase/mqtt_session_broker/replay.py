from __future__ import annotations

from .models import BrokerState, MqttEvent


def replay_mqtt_events(events: list[MqttEvent]) -> BrokerState:
    return BrokerState(events=tuple(events))
