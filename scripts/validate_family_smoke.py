#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


REQUIRED_PATHS = (
    "instruction.md",
    "task.toml",
    "environment/Dockerfile",
    "environment/codebase",
    "solution/solve.sh",
    "solution/files",
    "tests/test.sh",
    "tests/verifier.py",
)


def digest_json(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_layout(task: Path) -> list[str]:
    errors = [relative for relative in REQUIRED_PATHS if not (task / relative).exists()]
    try:
        config = tomllib.loads((task / "task.toml").read_text())
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        return [*errors, f"invalid task.toml: {exc}"]
    if config.get("schema_version") != "1.3":
        errors.append("schema_version must be 1.3")
    if config.get("metadata", {}).get("family") not in {
        "synthetic-repair",
        "nl2repo-lite",
        "repo-reproduction",
    }:
        errors.append("unsupported or missing metadata.family")
    if config.get("environment", {}).get("network_mode") != "no-network":
        errors.append("environment.network_mode must be no-network")
    verifier = config.get("verifier", {})
    if verifier.get("environment_mode") != "shared":
        errors.append("verifier.environment_mode must be shared")
    if verifier.get("network_mode") != "no-network":
        errors.append("verifier.network_mode must be no-network")
    return errors


def run_verifier(task: Path, workspace: Path, reward_dir: Path) -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "SWEFOUNDRY_REWARD_DIR": str(reward_dir),
        "SWEFOUNDRY_WORKSPACE": str(workspace),
    })
    completed = subprocess.run(
        [sys.executable, "-I", str(task / "tests/verifier.py")],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    reward_path = reward_dir / "reward.json"
    if completed.returncode != 0 or not reward_path.is_file():
        raise RuntimeError(
            f"verifier failed: rc={completed.returncode} "
            f"stdout={completed.stdout[-500:]} stderr={completed.stderr[-500:]}"
        )
    return json.loads(reward_path.read_text())


def run_attempt(task: Path, apply_oracle: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"swefoundry-{task.name}-") as tmp_name:
        temp = Path(tmp_name)
        workspace = temp / "workspace"
        shutil.copytree(task / "environment/codebase", workspace)
        if apply_oracle:
            env = dict(os.environ)
            env["SWEFOUNDRY_WORKSPACE"] = str(workspace)
            completed = subprocess.run(
                ["sh", str(task / "solution/solve.sh")],
                cwd=task,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"oracle solve failed: {completed.stderr[-500:]}")
        return run_verifier(task, workspace, temp / "reward")


def audit_task(task: Path) -> dict:
    layout_errors = validate_layout(task)
    if layout_errors:
        return {"task_id": task.name, "passed": False, "layout_errors": layout_errors}
    starter = run_attempt(task, apply_oracle=False)
    oracle_runs = [run_attempt(task, apply_oracle=True) for _ in range(2)]
    passed = (
        starter.get("reward", 1.0) < 1.0
        and all(run.get("reward") == 1.0 for run in oracle_runs)
        and digest_json(oracle_runs[0]) == digest_json(oracle_runs[1])
    )
    return {
        "task_id": task.name,
        "passed": passed,
        "starter_reward": starter.get("reward"),
        "oracle_rewards": [run.get("reward") for run in oracle_runs],
        "deterministic": digest_json(oracle_runs[0]) == digest_json(oracle_runs[1]),
        "case_count": len(oracle_runs[0].get("cases", {})),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("examples/family-smoke-v1/tasks"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tasks = sorted(path for path in args.root.iterdir() if (path / "task.toml").is_file())
    reports = [audit_task(task.resolve()) for task in tasks]
    summary = {
        "schema_version": "1.0",
        "passed": bool(reports) and all(report["passed"] for report in reports),
        "task_count": len(reports),
        "tasks": reports,
    }
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
