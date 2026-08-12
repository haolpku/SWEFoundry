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
    module = importlib.import_module("routekit")
    routes = module.compile_routes([
        ("wild", "/users/*rest"),
        ("param", "/users/:id"),
        ("new", "/users/new"),
        ("root", "/"),
    ])
    cases = {
        "static_precedence": module.match(routes, "/users/new") == {"name": "new", "params": {}},
        "parameter": module.match(routes, "/users/42") == {"name": "param", "params": {"id": "42"}},
        "wildcard": module.match(routes, "/users/a/b") == {"name": "wild", "params": {"rest": "a/b"}},
        "empty_wildcard": module.match(module.compile_routes([("files", "/files/*path")]), "/files") == {"name": "files", "params": {"path": ""}},
        "root": module.match(routes, "/") == {"name": "root", "params": {}},
        "trailing_slash": module.match(routes, "/users/42/") == {"name": "param", "params": {"id": "42"}},
        "duplicate_rejected": raises_value_error(lambda: module.compile_routes([("a", "/x"), ("b", "/x")])),
        "nonfinal_wildcard_rejected": raises_value_error(lambda: module.compile_routes([("a", "/x/*rest/y")])),
        "invalid_path_rejected": raises_value_error(lambda: module.match(routes, "users/42")),
        "missing": module.match(routes, "/other") is None,
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
