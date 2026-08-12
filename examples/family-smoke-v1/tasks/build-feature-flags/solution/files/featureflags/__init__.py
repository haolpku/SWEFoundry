from __future__ import annotations

from typing import Any


def _condition_matches(condition: object, context: dict[str, Any]) -> bool:
    if not isinstance(condition, dict) or set(condition) != {"key", "op", "value"}:
        raise ValueError("invalid condition")
    key, operator, expected = condition["key"], condition["op"], condition["value"]
    if not isinstance(key, str) or not key or not isinstance(operator, str):
        raise ValueError("invalid condition")
    if operator == "eq":
        return key in context and context[key] == expected
    if operator == "in":
        if not isinstance(expected, list):
            raise ValueError("in expects a list")
        return key in context and context[key] in expected
    if operator == "exists":
        if not isinstance(expected, bool):
            raise ValueError("exists expects a boolean")
        return (key in context) is expected
    raise ValueError("unknown operator")


def evaluate(flag: dict, context: dict) -> bool:
    if not isinstance(flag, dict) or not isinstance(context, dict):
        raise ValueError("flag and context must be dictionaries")
    if "default" not in flag or not isinstance(flag["default"], bool):
        raise ValueError("default must be boolean")
    if set(flag) - {"default", "rules"}:
        raise ValueError("unknown flag field")
    rules = flag.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("rules must be a list")
    validated = []
    for position, rule in enumerate(rules):
        if not isinstance(rule, dict) or set(rule) != {"priority", "value", "all"}:
            raise ValueError("invalid rule")
        if isinstance(rule["priority"], bool) or not isinstance(rule["priority"], int):
            raise ValueError("priority must be an integer")
        if not isinstance(rule["value"], bool) or not isinstance(rule["all"], list):
            raise ValueError("invalid rule value or conditions")
        validated.append((rule["priority"], position, rule))
    for _, _, rule in sorted(validated, key=lambda item: (-item[0], item[1])):
        if all(_condition_matches(condition, context) for condition in rule["all"]):
            return rule["value"]
    return flag["default"]


__all__ = ["evaluate"]
