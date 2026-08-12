from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from ..records import LineageEdge, TaskRecord, content_hash
from .base import FamilyDescriptor, common_profile, read_json_rows
from .production import SAFE_IMAGE


SAFE_REPO = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
SAFE_COMMIT = re.compile(r"^[0-9a-fA-F]{7,40}$")
SAFE_CONTAINER_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")


def _test_list(value: object) -> list[str]:
    if isinstance(value, str):
        parsed = json.loads(value)
        return [str(item) for item in parsed]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _task_slug(instance_id: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", instance_id.casefold()).strip("-")[:60]
    suffix = hashlib.sha256(instance_id.encode()).hexdigest()[:8]
    return f"swe-{stem}-{suffix}"


def _verifier_source(test_command: str, tests: list[str]) -> str:
    import shlex
    command_parts = shlex.split(test_command)
    if command_parts.count("{test}") != 1:
        raise ValueError("test_command must contain exactly one standalone {test} placeholder")
    return f'''from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

TEST_COMMAND = {command_parts!r}
TESTS = {tests!r}


def main() -> int:
    workspace = Path(os.environ.get("SWEFOUNDRY_WORKSPACE", "/app/workspace"))
    cases = {{}}
    for test in TESTS:
        command = [test if part == "{{test}}" else part for part in TEST_COMMAND]
        result = subprocess.run(command, cwd=workspace, text=True, capture_output=True)
        cases[test] = {{
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
        }}
    reward = sum(item["passed"] for item in cases.values()) / len(cases) if cases else 0.0
    payload = {{"reward": reward, "passed": reward == 1.0, "cases": cases}}
    reward_dir = Path(os.environ.get("SWEFOUNDRY_REWARD_DIR", "/logs/verifier"))
    reward_dir.mkdir(parents=True, exist_ok=True)
    (reward_dir / "reward.txt").write_text(f"{{reward:.6f}}\\n")
    (reward_dir / "reward.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _dockerfile(row: dict, repo_url: str, base_commit: str) -> str:
    bug_patch = str(row.get("bug_patch") or "")
    image = row.get("image_name")
    if image:
        image = str(image)
        repo_path = str(row.get("repo_path", "/testbed"))
        if (
            not SAFE_IMAGE.fullmatch(image)
            or not SAFE_CONTAINER_PATH.fullmatch(repo_path)
            or ".." in Path(repo_path).parts
        ):
            raise ValueError("unsafe SWE-bench image or repository path")
        setup = f"FROM {image}\nUSER root\nRUN mkdir -p /app && cp -a {repo_path} /app/workspace\n"
    else:
        if not SAFE_REPO.fullmatch(repo_url) or not SAFE_COMMIT.fullmatch(base_commit):
            raise ValueError("source-built SWE task requires a GitHub URL and hexadecimal pinned commit")
        setup = (
            "FROM python:3.11-slim\n"
            "RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*\n"
            f"RUN git clone {repo_url} /app/workspace && cd /app/workspace && git checkout {base_commit}\n"
        )
    apply_bug = "COPY bug.patch /tmp/bug.patch\nRUN if [ -s /tmp/bug.patch ]; then cd /app/workspace && git apply /tmp/bug.patch; fi\n" if bug_patch else ""
    return setup + apply_bug + "WORKDIR /app/workspace\n"


def _write_swe_task(row: dict, record: TaskRecord, output: Path) -> Path:
    instance_id = str(row.get("instance_id") or row.get("task_id"))
    task_root = output / _task_slug(instance_id)
    if task_root.exists():
        raise FileExistsError(f"refusing to overwrite task: {task_root}")
    repo = str(row.get("repo") or row.get("repo_url") or "")
    repo_url = repo if "://" in repo else f"https://github.com/{repo}"
    base_commit = str(row.get("base_commit") or "")
    tests = [*_test_list(row.get("FAIL_TO_PASS", [])), *_test_list(row.get("PASS_TO_PASS", []))]
    if not tests:
        raise ValueError(f"{instance_id}: no tests declared")
    patch = str(row.get("patch") or "")
    if not patch:
        raise ValueError(f"{instance_id}: gold patch is required for production QA")
    for directory in ("environment", "solution", "tests"):
        (task_root / directory).mkdir(parents=True, exist_ok=True)
    (task_root / "instruction.md").write_text(record.instruction + "\n", encoding="utf-8")
    (task_root / "environment/Dockerfile").write_text(_dockerfile(row, repo_url, base_commit), encoding="utf-8")
    (task_root / "environment/bug.patch").write_text(str(row.get("bug_patch") or ""), encoding="utf-8")
    (task_root / "solution/gold.patch").write_text(patch, encoding="utf-8")
    (task_root / "solution/solve.sh").write_text(
        '#!/bin/sh\nset -eu\nworkspace="${SWEFOUNDRY_WORKSPACE:-/app/workspace}"\ncd "$workspace"\ngit apply "$(dirname "$0")/gold.patch"\n',
        encoding="utf-8",
    )
    (task_root / "tests/verifier.py").write_text(_verifier_source(str(row["test_command"]), tests), encoding="utf-8")
    (task_root / "tests/test.sh").write_text(
        '#!/bin/sh\nset -eu\npython3 "${SWEFOUNDRY_TEST_ROOT:-/tests}/verifier.py"\nsync\n',
        encoding="utf-8",
    )
    task_toml = f'''schema_version = "1.3"
artifacts = ["/app/workspace"]

[task]
name = "swefoundry/{_task_slug(instance_id)}"
description = {json.dumps(record.instruction.splitlines()[0][:200])}
authors = [{{ name = "SWEFoundry" }}]
keywords = ["swe-bench", "repo-repair"]

[metadata]
family = "swe-bench"
language = "mixed"
horizon = "medium"
reward_type = "test_fraction"
provenance = "{instance_id}"

[verifier]
timeout_sec = 1800.0
environment_mode = "shared"
network_mode = "no-network"

[agent]
timeout_sec = 7200.0
max_steps = 500

[environment]
build_timeout_sec = 1800.0
os = "linux"
cpus = 4
memory_mb = 8192
storage_mb = 16384
gpus = 0
network_mode = "no-network"
workdir = "/app/workspace"
'''
    (task_root / "task.toml").write_text(task_toml, encoding="utf-8")
    (task_root / "swefoundry-task-record.json").write_text(
        json.dumps(record.as_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return task_root


class SWEBenchFamily:
    descriptor = FamilyDescriptor(
        family_id="swe-bench",
        task_shape="pinned repository issue resolution",
        import_supported=True,
        harbor_native=False,
        generation_tier="P0",
        expert_requirement="low_for_mutation_medium_for_real_issues",
    )

    def import_records(self, source: Path, *, source_ref: str, dataset_version: str) -> list[TaskRecord]:
        records = []
        for row in read_json_rows(source):
            task_id = str(row.get("instance_id") or row.get("task_id") or "")
            repo = str(row.get("repo") or row.get("repo_url") or "")
            repo_url = repo if "://" in repo else f"https://github.com/{repo}"
            base_commit = str(row.get("base_commit") or "")
            instruction = str(row.get("problem_statement") or row.get("instruction") or "").strip()
            artifact_hash = content_hash(row)
            records.append(TaskRecord(
                task_id=task_id,
                task_version=dataset_version,
                family=self.descriptor.family_id,
                instruction=instruction,
                workspace_kind="repo_snapshot",
                workspace={"repo_url": repo_url, "base_commit": base_commit, "materializer": "swe_bench"},
                environment={
                    "image": row.get("image_name"),
                    "version": row.get("version"),
                    "network_mode": "no-network",
                },
                verifier={
                    "adapter": "swe_bench",
                    "fail_to_pass": _test_list(row.get("FAIL_TO_PASS", [])),
                    "pass_to_pass": _test_list(row.get("PASS_TO_PASS", [])),
                },
                provenance={"source_family": "swe-bench", "source_ref": source_ref},
                profile={"objective_type": "repo_repair", "horizon": "medium", "reward_shape": "test_fraction"},
                lineage=(LineageEdge("imported_from", artifact_hash),),
            ))
        return records

    def validate_record(self, record: TaskRecord) -> list[str]:
        errors = common_profile(record)
        if record.workspace_kind != "repo_snapshot":
            errors.append(f"{record.task_id}: swe-bench requires repo_snapshot workspace")
        if not record.verifier.get("fail_to_pass"):
            errors.append(f"{record.task_id}: swe-bench requires FAIL_TO_PASS tests")
        return errors

    def package_for_harbor(self, source: Path, output: Path, *, source_ref: str, dataset_version: str) -> list[Path]:
        rows = read_json_rows(source)
        records = self.import_records(source, source_ref=source_ref, dataset_version=dataset_version)
        output.mkdir(parents=True, exist_ok=True)
        return [_write_swe_task(row, record, output) for row, record in zip(rows, records)]
