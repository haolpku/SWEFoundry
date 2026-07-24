from __future__ import annotations

from types import MappingProxyType

from .matching import match_mqtt_subscriptions
from .models import BrokerState, Delivery, MqttEvent, Session, Subscription


def _message_id(event: MqttEvent) -> str:
    return event.message_id or f"seq-{event.seq}"


def _replace_subscription(session: Session, sub: Subscription) -> Session:
    kept = tuple(existing for existing in session.subscriptions if existing.identifier != sub.identifier)
    return Session(session.client_id, session.connected, session.clean_start, tuple(sorted(kept + (sub,), key=lambda s: s.identifier)), session.queue, session.expired)


def _set_queue(session: Session, queue: tuple[Delivery, ...]) -> Session:
    return Session(session.client_id, session.connected, session.clean_start, session.subscriptions, queue, session.expired)


def _deliver(event: MqttEvent, sessions: dict[str, Session], retained: bool) -> list[Delivery]:
    deliveries: list[Delivery] = []
    topic = event.topic or ""
    all_subs = [sub for session in sessions.values() for sub in session.subscriptions]
    ids = set(match_mqtt_subscriptions(all_subs, topic))
    for client_id in sorted(sessions):
        session = sessions[client_id]
        matching = [sub for sub in session.subscriptions if sub.identifier in ids and match_mqtt_subscriptions([sub], topic)]
        if not matching:
            continue
        qos = max([event.qos] + [sub.qos for sub in matching])
        status = "pending" if qos == 1 else "delivered"
        delivery = Delivery(client_id, topic, event.payload, qos, event.seq, _message_id(event), status, retained)
        if session.connected:
            deliveries.append(delivery)
        elif session.subscriptions and any(sub.durable for sub in matching):
            session_queue = session.queue
            if qos == 1 and any(old.message_id == delivery.message_id and old.topic == delivery.topic for old in session_queue):
                continue
            sessions[client_id] = _set_queue(session, tuple(sorted(session_queue + (delivery,), key=lambda d: (d.seq, d.client_id, d.message_id))))
    return deliveries


def replay_mqtt_events(events: list[MqttEvent]) -> BrokerState:
    ordered = sorted(events, key=lambda event: event.seq)
    sessions: dict[str, Session] = {}
    retained: dict[str, Delivery] = {}
    tombstones: list[str] = []
    deliveries: list[Delivery] = []
    expired: list[str] = []
    for event in ordered:
        client_id = event.client_id
        if event.action == "connect" and client_id:
            old = sessions.get(client_id, Session(client_id))
            queue = () if event.clean_start else old.queue
            subs = () if event.clean_start else old.subscriptions
            sessions[client_id] = Session(client_id, True, event.clean_start, subs, queue, False)
            deliveries.extend(queue)
            sessions[client_id] = _set_queue(sessions[client_id], ())
        elif event.action == "disconnect" and client_id in sessions:
            s = sessions[client_id]
            sessions[client_id] = Session(s.client_id, False, s.clean_start, s.subscriptions, s.queue, s.expired)
        elif event.action == "subscribe" and client_id and event.topic_filter:
            session = sessions.get(client_id, Session(client_id))
            sub = Subscription(client_id, event.subscription_id or event.topic_filter, event.topic_filter, event.qos, event.durable)
            sessions[client_id] = _replace_subscription(session, sub)
            for retained_delivery in [retained[t] for t in sorted(retained) if match_mqtt_subscriptions([sub], t)]:
                deliveries.append(Delivery(client_id, retained_delivery.topic, retained_delivery.payload, max(sub.qos, retained_delivery.qos), event.seq, retained_delivery.message_id, "delivered", True))
        elif event.action == "publish" and event.topic:
            if event.retain:
                if event.payload in (None, ""):
                    retained.pop(event.topic, None)
                    tombstones.append(event.topic)
                else:
                    retained[event.topic] = Delivery("$retained", event.topic, event.payload, event.qos, event.seq, _message_id(event), "delivered", True)
            deliveries.extend(_deliver(event, sessions, False))
        elif event.action == "acknowledge" and client_id:
            ack = event.ack_id or event.message_id
            updated: list[Delivery] = []
            for delivery in deliveries:
                if delivery.client_id == client_id and delivery.message_id == ack and delivery.status == "pending":
                    updated.append(Delivery(delivery.client_id, delivery.topic, delivery.payload, delivery.qos, delivery.seq, delivery.message_id, "acked", delivery.retained))
                else:
                    updated.append(delivery)
            deliveries = updated
        elif event.action == "expire" and client_id:
            expired.append(client_id)
            old = sessions.get(client_id, Session(client_id))
            sessions[client_id] = Session(client_id, False, old.clean_start, old.subscriptions, old.queue, True)
    return BrokerState(events=tuple(ordered), sessions=MappingProxyType(dict(sorted(sessions.items()))), retained=MappingProxyType(dict(sorted(retained.items()))), retained_tombstones=tuple(sorted(set(tombstones))), deliveries=tuple(sorted(deliveries, key=lambda d: (d.seq, d.client_id, d.message_id, d.retained))), expired_clients=tuple(sorted(set(expired))))
