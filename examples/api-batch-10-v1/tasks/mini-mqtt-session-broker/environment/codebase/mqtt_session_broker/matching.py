from __future__ import annotations

from .exceptions import MqttValidationError
from .models import Subscription


def _valid_filter(topic_filter: str) -> None:
    if not isinstance(topic_filter, str) or not topic_filter:
        raise MqttValidationError("invalid topic filter")


def _matches(topic_filter: str, topic: str) -> bool:
    if topic_filter == topic:
        return True
    if "#" in topic_filter:
        return topic.startswith(topic_filter.replace("#", ""))
    return False


def match_mqtt_subscriptions(subscriptions: list[Subscription], topic: str) -> list[str]:
    if not isinstance(topic, str) or not topic:
        raise MqttValidationError("invalid topic")
    result: list[str] = []
    for sub in subscriptions:
        _valid_filter(sub.topic_filter)
        if _matches(sub.topic_filter, topic):
            result.append(sub.identifier)
    return sorted(result)
