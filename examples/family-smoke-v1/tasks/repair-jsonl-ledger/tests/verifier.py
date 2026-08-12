from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(os.environ.get("SWEFOUNDRY_WORKSPACE", "/app/workspace")).resolve()))


def raises_value_error(callable_) -> bool:
    try:
        callable_()
    except ValueError:
        return True
    return False


def main() -> int:
    module = importlib.import_module("jsonl_ledger")
    base = ['{"account":"b","delta":3,"id":"1"}\n']
    event = {"id": "2", "account": "a", "delta": -3}
    appended = module.append_event(base, event)
    cases = {
        "append_is_immutable": base == ['{"account":"b","delta":3,"id":"1"}\n'],
        "canonical_json": appended[-1] == '{"account":"a","delta":-3,"id":"2"}\n',
        "replay_balances": module.replay(appended) == {"balances": {"a": -3, "b": 3}, "event_count": 2},
        "duplicate_append": raises_value_error(lambda: module.append_event(base, {"id": "1", "account": "x", "delta": 1})),
        "duplicate_replay": raises_value_error(lambda: module.replay([base[0], base[0]])),
        "reject_bool": raises_value_error(lambda: module.append_event([], {"id": "x", "account": "a", "delta": True})),
        "reject_extra_field": raises_value_error(lambda: module.append_event([], {"id": "x", "account": "a", "delta": 1, "note": "x"})),
        "reject_bad_json": raises_value_error(lambda: module.replay(["not-json\n"])),
    }
    reward = sum(cases.values()) / len(cases)
    output = {"reward": reward, "passed": reward == 1.0, "cases": cases}
    reward_dir = Path(os.environ.get("SWEFOUNDRY_REWARD_DIR", "/logs/verifier"))
    reward_dir.mkdir(parents=True, exist_ok=True)
    (reward_dir / "reward.txt").write_text(f"{reward:.6f}\n")
    (reward_dir / "reward.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
