from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


TASK_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]*$")


def safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe relative path: {value!r}")
    return path.as_posix()


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative, content in sorted(files.items()):
        path = root / safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


@dataclass(frozen=True)
class HarborBuildSpec:
    task_id: str
    family: str
    instruction: str
    starter_files: dict[str, str]
    solution_files: dict[str, str]
    verifier_files: dict[str, str]
    base_image: str = "python:3.11-slim"
    horizon: str = "medium"
    reward_shape: str = "test_fraction"
    language: str = "python"
    agent_timeout_sec: int = 1800
    verifier_timeout_sec: int = 300
    cpus: int = 2
    memory_mb: int = 4096
    storage_mb: int = 4096
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not TASK_ID.fullmatch(self.task_id):
            raise ValueError(f"invalid task_id: {self.task_id!r}")
        if not self.instruction.strip():
            raise ValueError("instruction must be non-empty")
        if not SAFE_IMAGE.fullmatch(self.base_image):
            raise ValueError(f"unsafe base image: {self.base_image!r}")
        if self.horizon not in {"short", "medium", "long", "ultra_long"}:
            raise ValueError(f"invalid horizon: {self.horizon}")
        if "verifier.py" not in self.verifier_files:
            raise ValueError("verifier_files must include verifier.py")
        for mapping in (self.starter_files, self.solution_files, self.verifier_files):
            for path in mapping:
                safe_path(path)


def compile_harbor_task(spec: HarborBuildSpec, output_root: Path) -> Path:
    spec.validate()
    task_root = output_root / spec.task_id
    if task_root.exists():
        raise FileExistsError(f"refusing to overwrite task: {task_root}")
    (task_root / "environment/codebase").mkdir(parents=True)
    (task_root / "solution/files").mkdir(parents=True)
    (task_root / "tests").mkdir(parents=True)
    _write_files(task_root / "environment/codebase", spec.starter_files)
    _write_files(task_root / "solution/files", spec.solution_files)
    _write_files(task_root / "tests", spec.verifier_files)

    dockerfile = f"""FROM {spec.base_image}
WORKDIR /app/workspace
COPY codebase/ /app/workspace/
"""
    (task_root / "environment/Dockerfile").write_text(dockerfile, encoding="utf-8")
    (task_root / "instruction.md").write_text(spec.instruction.strip() + "\n", encoding="utf-8")

    solve = """#!/bin/sh
set -eu
workspace="${SWEFOUNDRY_WORKSPACE:-/app/workspace}"
mkdir -p "$workspace"
cp -R "$(dirname "$0")/files/." "$workspace/"
"""
    (task_root / "solution/solve.sh").write_text(solve, encoding="utf-8")
    test_shell = """#!/bin/sh
set -eu
test_root="${SWEFOUNDRY_TEST_ROOT:-/tests}"
python3 "$test_root/verifier.py"
sync
"""
    (task_root / "tests/test.sh").write_text(test_shell, encoding="utf-8")

    task_toml = f'''schema_version = "1.3"
artifacts = ["/app/workspace"]

[task]
name = "swefoundry/{spec.task_id}"
description = {_toml_string(spec.instruction.strip().splitlines()[0][:200])}
authors = [{{ name = "SWEFoundry" }}]
keywords = ["{spec.family}", "{spec.horizon}", "{spec.language}"]

[metadata]
family = "{spec.family}"
language = "{spec.language}"
horizon = "{spec.horizon}"
reward_type = "{spec.reward_shape}"
provenance = "generated"

[verifier]
timeout_sec = {float(spec.verifier_timeout_sec)}
environment_mode = "shared"
network_mode = "no-network"

[agent]
timeout_sec = {float(spec.agent_timeout_sec)}
max_steps = 500

[environment]
build_timeout_sec = 900.0
os = "linux"
cpus = {spec.cpus}
memory_mb = {spec.memory_mb}
storage_mb = {spec.storage_mb}
gpus = 0
network_mode = "no-network"
workdir = "/app/workspace"
'''
    (task_root / "task.toml").write_text(task_toml, encoding="utf-8")
    (task_root / "production-metadata.json").write_text(
        json.dumps(spec.metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return task_root


def spec_from_recipe(row: dict[str, Any], *, expected_family: str) -> HarborBuildSpec:
    family = str(row.get("family") or expected_family)
    if family != expected_family:
        raise ValueError(f"recipe family {family!r} does not match {expected_family!r}")
    return HarborBuildSpec(
        task_id=str(row["task_id"]),
        family=family,
        instruction=str(row["instruction"]),
        starter_files={str(k): str(v) for k, v in row.get("starter_files", {}).items()},
        solution_files={str(k): str(v) for k, v in row.get("solution_files", {}).items()},
        verifier_files={str(k): str(v) for k, v in row.get("verifier_files", {}).items()},
        base_image=str(row.get("base_image", "python:3.11-slim")),
        horizon=str(row.get("horizon", "medium")),
        reward_shape=str(row.get("reward_shape", "test_fraction")),
        language=str(row.get("language", "python")),
        agent_timeout_sec=int(row.get("agent_timeout_sec", 1800)),
        verifier_timeout_sec=int(row.get("verifier_timeout_sec", 300)),
        cpus=int(row.get("cpus", 2)),
        memory_mb=int(row.get("memory_mb", 4096)),
        storage_mb=int(row.get("storage_mb", 4096)),
        metadata=dict(row.get("provenance", {})),
    )
