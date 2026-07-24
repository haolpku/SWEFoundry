from __future__ import annotations

from .exceptions import MqttValidationError
from .models import Subscription


def _validate_topic(topic: str) -> list[str]:
    if not isinstance(topic, str) or not topic or topic.startswith("/") or topic.endswith("/") or "//" in topic:
        raise MqttValidationError("invalid topic")
    if "+" in topic or "#" in topic:
        raise MqttValidationError("topic cannot contain wildcards")
    return topic.split("/")


def _validate_filter(topic_filter: str) -> list[str]:
    if not isinstance(topic_filter, str) or not topic_filter or topic_filter.startswith("/") or topic_filter.endswith("/") or "//" in topic_filter:
        raise MqttValidationError("invalid topic filter")
    levels = topic_filter.split("/")
    for index, level in enumerate(levels):
        if level == "#" and index != len(levels) - 1:
            raise MqttValidationError("multi-level wildcard must be terminal")
        if "#" in level and level != "#":
            raise MqttValidationError("multi-level wildcard must occupy a whole level")
        if "+" in level and level != "+":
            raise MqttValidationError("single-level wildcard must occupy a whole level")
    return levels


def _matches(filter_levels: list[str], topic_levels: list[str]) -> bool:
    topic_index = 0
    for level in filter_levels:
        if level == "#":
            return True
        if topic_index >= len(topic_levels):
            return False
        if level != "+" and level != topic_levels[topic_index]:
            return False
        topic_index += 1
    return topic_index == len(topic_levels)


def match_mqtt_subscriptions(subscriptions: list[Subscription], topic: str) -> list[str]:
    topic_levels = _validate_topic(topic)
    matched: list[str] = []
    for sub in subscriptions:
        levels = _validate_filter(sub.topic_filter)
        if _matches(levels, topic_levels):
            matched.append(sub.identifier)
    return sorted(matched)
