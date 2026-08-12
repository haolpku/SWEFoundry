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
    try:
        evaluate = importlib.import_module("featureflags").evaluate
    except (ImportError, AttributeError):
        evaluate = None
    if evaluate is None:
        cases = {name: False for name in ("default", "priority", "stable_tie", "eq", "in", "exists", "empty_all", "validation")}
    else:
        priority_flag = {"default": False, "rules": [
            {"priority": 1, "value": False, "all": []},
            {"priority": 9, "value": True, "all": [{"key": "tier", "op": "eq", "value": "pro"}]},
        ]}
        tie_flag = {"default": False, "rules": [
            {"priority": 4, "value": True, "all": []},
            {"priority": 4, "value": False, "all": []},
        ]}
        cases = {
            "default": evaluate({"default": True}, {}) is True,
            "priority": evaluate(priority_flag, {"tier": "pro"}) is True,
            "stable_tie": evaluate(tie_flag, {}) is True,
            "eq": evaluate({"default": False, "rules": [{"priority": 1, "value": True, "all": [{"key": "x", "op": "eq", "value": 3}]}]}, {"x": 3}) is True,
            "in": evaluate({"default": False, "rules": [{"priority": 1, "value": True, "all": [{"key": "r", "op": "in", "value": ["cn", "sg"]}]}]}, {"r": "sg"}) is True,
            "exists": evaluate({"default": True, "rules": [{"priority": 1, "value": False, "all": [{"key": "blocked", "op": "exists", "value": False}]}]}, {}) is False,
            "empty_all": evaluate({"default": False, "rules": [{"priority": 0, "value": True, "all": []}]}, {}) is True,
            "validation": raises_value_error(lambda: evaluate({"default": False, "rules": [{"priority": 1, "value": True, "all": [{"key": "x", "op": "in", "value": "bad"}]}]}, {})),
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
