from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED = (
    "instruction.md", "task.toml", "environment/Dockerfile",
    "solution/solve.sh", "tests/test.sh", "tests/verifier.py",
)


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_production_layout(task: Path) -> list[str]:
    errors = [f"missing {relative}" for relative in REQUIRED if not (task / relative).exists()]
    if not (task / "environment/codebase").is_dir():
        errors.append("local QA requires environment/codebase; use Harbor Oracle QA for runtime-materialized SWE tasks")
    return errors


def _attempt(task: Path, *, oracle: bool, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"swefoundry-qa-{task.name}-") as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        shutil.copytree(task / "environment/codebase", workspace)
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "SWEFOUNDRY_WORKSPACE": str(workspace),
            "SWEFOUNDRY_REWARD_DIR": str(root / "reward"),
            "SWEFOUNDRY_TEST_ROOT": str(task / "tests"),
        }
        if oracle:
            result = subprocess.run(
                ["sh", str(task / "solution/solve.sh")], cwd=task, env=env,
                text=True, capture_output=True, timeout=timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Oracle failed: {result.stderr[-500:]}")
        result = subprocess.run(
            [sys.executable, "-I", str(task / "tests/verifier.py")], cwd=workspace, env=env,
            text=True, capture_output=True, timeout=timeout,
        )
        reward = root / "reward/reward.json"
        if result.returncode != 0 or not reward.is_file():
            raise RuntimeError(f"verifier failed: rc={result.returncode}; {result.stderr[-500:]}")
        return json.loads(reward.read_text(encoding="utf-8"))


def audit_production_task(task: Path, *, repeats: int = 2, timeout: int = 300) -> dict:
    errors = validate_production_layout(task)
    if errors:
        return {"task_id": task.name, "passed": False, "errors": errors}
    try:
        starter = _attempt(task, oracle=False, timeout=timeout)
        oracle = [_attempt(task, oracle=True, timeout=timeout) for _ in range(repeats)]
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as exc:
        return {"task_id": task.name, "passed": False, "errors": [str(exc)]}
    rewards = [float(item.get("reward", -1)) for item in oracle]
    deterministic = len({_digest(item) for item in oracle}) == 1
    passed = float(starter.get("reward", 1)) < 1 and all(value == 1 for value in rewards) and deterministic
    return {
        "task_id": task.name,
        "passed": passed,
        "starter_reward": starter.get("reward"),
        "oracle_rewards": rewards,
        "deterministic": deterministic,
        "errors": [] if passed else ["Starter/Oracle/determinism gate failed"],
    }
