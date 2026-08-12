import json


_FIELDS = {"id", "account", "delta"}


def _validate(event: object) -> dict:
    if not isinstance(event, dict) or set(event) != _FIELDS:
        raise ValueError("event must contain exactly id, account, and delta")
    if not isinstance(event["id"], str) or not event["id"]:
        raise ValueError("id must be a non-empty string")
    if not isinstance(event["account"], str) or not event["account"]:
        raise ValueError("account must be a non-empty string")
    if isinstance(event["delta"], bool) or not isinstance(event["delta"], int):
        raise ValueError("delta must be an integer")
    return event


def _decode(line: str) -> dict:
    try:
        return _validate(json.loads(line))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError("invalid ledger event") from exc


def append_event(lines: list[str], event: dict) -> list[str]:
    valid = _validate(event)
    identifiers = {_decode(line)["id"] for line in lines}
    if valid["id"] in identifiers:
        raise ValueError("duplicate event id")
    encoded = json.dumps(valid, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return [*lines, encoded + "\n"]


def replay(lines: list[str]) -> dict:
    balances: dict[str, int] = {}
    seen: set[str] = set()
    for line in lines:
        event = _decode(line)
        if event["id"] in seen:
            raise ValueError("duplicate event id")
        seen.add(event["id"])
        account = event["account"]
        balances[account] = balances.get(account, 0) + event["delta"]
    return {
        "balances": {key: balances[key] for key in sorted(balances)},
        "event_count": len(lines),
    }
