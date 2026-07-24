from __future__ import annotations

import json
import re
from typing import Any

from .exceptions import MqttParseError, MqttValidationError
from .models import MqttEvent

_CLIENT_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,23}$")
_ACTIONS = {"connect", "subscribe", "publish", "acknowledge", "disconnect", "expire"}


def _items(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MqttParseError(str(exc)) from exc
    if isinstance(data, dict) and "events" in data:
        data = data["events"]
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        raise MqttParseError("events must be a JSON list of objects")
    return data


def _client(value: Any) -> str:
    if not isinstance(value, str) or not _CLIENT_RE.fullmatch(value):
        raise MqttValidationError("invalid client identifier")
    return value


def _topic(value: Any, *, allow_wildcards: bool) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or value.endswith("/") or "//" in value:
        raise MqttValidationError("invalid topic")
    if not allow_wildcards and ("+" in value or "#" in value):
        raise MqttValidationError("publish topics cannot contain wildcards")
    for level in value.split("/"):
        if not level:
            raise MqttValidationError("empty topic level")
        if allow_wildcards:
            if "#" in level and level != "#":
                raise MqttValidationError("malformed multi-level wildcard")
            if "+" in level and level != "+":
                raise MqttValidationError("malformed single-level wildcard")
    if allow_wildcards and "#" in value and value.split("/")[-1] != "#":
        raise MqttValidationError("multi-level wildcard must be terminal")
    return value


def _text_or_none(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MqttValidationError(f"{name} must be a string")
    return value


def parse_mqtt_events(text: str) -> list[MqttEvent]:
    events: list[MqttEvent] = []
    seen: set[int] = set()
    for raw in _items(text):
        seq = raw.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool):
            raise MqttValidationError("event seq must be an integer")
        if seq in seen:
            raise MqttValidationError("duplicate event seq")
        seen.add(seq)
        action = raw.get("action")
        if action not in _ACTIONS:
            raise MqttValidationError("unknown action")
        client_id = _client(raw["client_id"]) if "client_id" in raw else None
        topic = _topic(raw["topic"], allow_wildcards=False) if "topic" in raw else None
        topic_filter = _topic(raw.get("filter", raw.get("topic_filter")), allow_wildcards=True) if ("filter" in raw or "topic_filter" in raw) else None
        subscription_id = _text_or_none(raw.get("subscription_id", raw.get("sub_id")), "subscription_id")
        payload = _text_or_none(raw.get("payload"), "payload")
        message_id = _text_or_none(raw.get("message_id"), "message_id")
        ack_id = _text_or_none(raw.get("ack_id", raw.get("message_id")), "ack_id")
        qos = raw.get("qos", 0)
        if not isinstance(qos, int) or isinstance(qos, bool):
            raise MqttValidationError("qos must be an integer")
        events.append(MqttEvent(seq=seq, action=action, client_id=client_id, topic=topic, topic_filter=topic_filter, subscription_id=subscription_id, qos=qos, payload=payload, retain=bool(raw.get("retain", False)), clean_start=bool(raw.get("clean_start", True)), durable=bool(raw.get("durable", True)), message_id=message_id, ack_id=ack_id))
    return sorted(events, key=lambda event: event.seq)
