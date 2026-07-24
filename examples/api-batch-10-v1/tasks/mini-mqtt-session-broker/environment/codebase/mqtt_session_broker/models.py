from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class MqttEvent:
    seq: int
    action: str
    client_id: str | None = None
    topic: str | None = None
    topic_filter: str | None = None
    subscription_id: str | None = None
    qos: int = 0
    payload: str | None = None
    retain: bool = False
    clean_start: bool = True
    durable: bool = True
    message_id: str | None = None
    ack_id: str | None = None


@dataclass(frozen=True)
class Subscription:
    client_id: str
    identifier: str
    topic_filter: str
    qos: int = 0
    durable: bool = True


@dataclass(frozen=True)
class Delivery:
    client_id: str
    topic: str
    payload: str | None
    qos: int
    seq: int
    message_id: str
    status: str = "delivered"
    retained: bool = False


@dataclass(frozen=True)
class Session:
    client_id: str
    connected: bool = False
    clean_start: bool = True
    subscriptions: tuple[Subscription, ...] = ()
    queue: tuple[Delivery, ...] = ()
    expired: bool = False


@dataclass(frozen=True)
class BrokerState:
    events: tuple[MqttEvent, ...] = ()
    sessions: Mapping[str, Session] = field(default_factory=lambda: MappingProxyType({}))
    retained: Mapping[str, Delivery] = field(default_factory=lambda: MappingProxyType({}))
    retained_tombstones: tuple[str, ...] = ()
    deliveries: tuple[Delivery, ...] = ()
    expired_clients: tuple[str, ...] = ()


@dataclass(frozen=True)
class MqttMigrationAdvice:
    category: str
    target: str
    detail: str
    seq: int = 0


@dataclass(frozen=True)
class MqttAuditReport:
    events: tuple[MqttEvent, ...]
    state: BrokerState
    advice: tuple[MqttMigrationAdvice, ...]
    deliveries: tuple[Delivery, ...]
    retained_topics: tuple[str, ...]
    sessions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": len(self.events),
            "deliveries": [d.__dict__ for d in self.deliveries],
            "retained_topics": list(self.retained_topics),
            "sessions": list(self.sessions),
            "advice": [a.__dict__ for a in self.advice],
        }
