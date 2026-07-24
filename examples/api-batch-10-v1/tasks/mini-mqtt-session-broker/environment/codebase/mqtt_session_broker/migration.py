from __future__ import annotations

from .models import BrokerState, MqttMigrationAdvice


def plan_mqtt_migration(state: BrokerState) -> list[MqttMigrationAdvice]:
    return []
