import json


def append_event(lines: list[str], event: dict) -> list[str]:
    """Append an event. This starter intentionally violates the contract."""
    lines.append(json.dumps(event) + "\n")
    return lines


def replay(lines: list[str]) -> dict:
    balances: dict[str, int] = {}
    seen: set[str] = set()
    for line in lines:
        event = json.loads(line)
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        balances[event["account"]] = balances.get(event["account"], 0) + event["delta"]
    return {"balances": balances, "event_count": len(lines)}
