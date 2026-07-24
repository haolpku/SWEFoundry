from __future__ import annotations

import json
import hashlib
import re
import tomllib
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .models import TaskFamily


REQUIRED_DIRS = (
    "environment",
    "workspace",
    "evidence",
    "generator",
    "solution",
    "tests",
    "anti_cheat",
    "nexus",
    "docs",
)
REQUIRED_FILES = (
    "task.json",
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "environment/workspace/app.py",
    "environment/workspace/README.md",
    "environment/evidence/contract.json",
    "environment/evidence/cases.json",
    "generator/generate.py",
    "solution/solve.sh",
    "solution/app.py",
    "tests/test.sh",
    "tests/verify.py",
    "nexus/run.yaml",
    "docs/curation-history.md",
    "docs/verifier-audit.md",
    "docs/failure-modes.md",
)
FORBIDDEN_INSTRUCTION = (
    "step by step",
    "you are a",
    "grep ",
    "cat /",
    "search the knowledge",
    "must search",
)
LEAK_MARKERS = ("/opt/oracle", "/opt/verifier", "hidden_tests", "reference solution")


@dataclass
class ValidationReport:
    task_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def _walk_text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.stat().st_size <= 2_000_000:
            try:
                yield path, path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def validate_task(root: Path) -> ValidationReport:
    report = ValidationReport(task_id=root.name)
    for name in REQUIRED_DIRS:
        if not (root / name).is_dir():
            report.errors.append(f"missing directory: {name}")
    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            report.errors.append(f"missing file: {name}")
    if report.errors:
        return report

    try:
        task = TaskFamily.load(root)
    except (OSError, ValueError, KeyError) as exc:
        report.errors.append(f"invalid task.json: {exc}")
        return report

    raw = task.raw
    required = {"schema_version", "id", "category", "status", "instruction", "paths", "stages", "quality"}
    missing = required - raw.keys()
    if missing:
        report.errors.append(f"task.json missing keys: {sorted(missing)}")
    if raw.get("schema_version") != "1.0":
        report.errors.append("schema_version must be 1.0")
    if raw.get("id") != root.name:
        report.errors.append("task id must match directory name")
    if raw.get("status") not in {
        "draft", "buildable", "oracle-passed", "verifier-audited", "rollout-qualified",
        "failure-analyzed", "human-approved", "released",
    }:
        report.errors.append("invalid status")

    paths = raw.get("paths", {})
    expected_paths = {
        "workspace": "/app/workspace",
        "evidence": "/app/evidence",
        "solution": "/solution",
        "tests": "/tests",
    }
    if paths != expected_paths:
        report.errors.append(f"paths must equal {expected_paths}")

    stages = raw.get("stages", [])
    if not 4 <= len(stages) <= 7:
        report.errors.append("task must define 4-7 stages")
    stage_ids = [stage.get("id") for stage in stages if isinstance(stage, dict)]
    if len(stage_ids) != len(set(stage_ids)):
        report.errors.append("stage ids must be unique")
    for stage in stages:
        if not isinstance(stage, dict) or len(stage.get("acceptance", [])) < 2:
            report.errors.append("every stage needs at least two acceptance statements")

    quality = raw.get("quality", {})
    if quality.get("minimum_behavioral_tests", 0) < 15:
        report.errors.append("minimum_behavioral_tests must be >= 15")
    if quality.get("minimum_anti_cheats", 0) < 4:
        report.errors.append("minimum_anti_cheats must be >= 4")
    if quality.get("rollouts", 0) < 10:
        report.errors.append("rollouts must be >= 10")
    if not 0 <= quality.get("max_pass_rate", 1) <= 0.3:
        report.errors.append("max_pass_rate must be in [0, 0.3]")

    instruction = task.instruction_path.read_text(encoding="utf-8").strip()
    words = instruction.split()
    if not 45 <= len(words) <= 120:
        report.errors.append(f"instruction must contain 45-120 words, got {len(words)}")
    if "/app/workspace" not in instruction or "/app/evidence" not in instruction:
        report.errors.append("instruction must mention /app/workspace and /app/evidence")
    if re.search(r"(^|\s)\.\.?/", instruction):
        report.errors.append("instruction contains a relative path")
    if re.search(r"(?m)^\s*#|```", instruction):
        report.errors.append("instruction contains Markdown scaffolding")
    lowered = instruction.lower()
    for phrase in FORBIDDEN_INSTRUCTION:
        if phrase in lowered:
            report.errors.append(f"instruction contains leading/how-to phrase: {phrase}")

    try:
        harbor_config = tomllib.loads((root / "task.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        report.errors.append(f"invalid task.toml: {exc}")
        harbor_config = {}
    if harbor_config.get("schema_version") == "1.3" and harbor_config.get("artifacts"):
        if "/app/workspace" not in harbor_config.get("artifacts", []):
            report.errors.append("Harbor schema 1.3 task must collect /app/workspace")
        verifier_config = harbor_config.get("verifier", {})
        if verifier_config.get("environment_mode") != "separate":
            report.errors.append("Harbor schema 1.3 task must use a separate verifier")
        if verifier_config.get("network_mode") != "no-network":
            report.errors.append("separate verifier must run without network access")
        if not (root / "tests/Dockerfile").is_file():
            report.errors.append("separate verifier requires tests/Dockerfile")
        environment_config = harbor_config.get("environment", {})
        if environment_config.get("network_mode") != "no-network":
            report.errors.append("agent environment must use no-network sandbox mode")
        timeout = environment_config and harbor_config.get("agent", {}).get("timeout_sec")
        if timeout is not None:
            suffix = (
                f"You have {int(timeout)} seconds to complete this task. "
                "Do not cheat by using online solutions or hints specific to this task."
            )
            if not instruction.endswith(suffix):
                report.errors.append("instruction is missing the Harbor timeout suffix")
        metadata = harbor_config.get("metadata", {})
        for field_name in (
            "difficulty_explanation",
            "solution_explanation",
            "verification_explanation",
            "category",
            "subcategory",
            "tags",
            "expert_time_estimate_hours",
        ):
            if not metadata.get(field_name):
                report.errors.append(f"task.toml metadata missing {field_name}")
        for field_name in ("author_name", "author_email", "relevant_experience"):
            if not metadata.get(field_name):
                report.warnings.append(f"human metadata pending: {field_name}")

    anti_cheats = sorted((root / "anti_cheat").glob("*.py"))
    if len(anti_cheats) < quality.get("minimum_anti_cheats", 4):
        report.errors.append(f"expected at least {quality.get('minimum_anti_cheats', 4)} anti-cheat scripts")

    for scope in (root / "workspace", root / "environment"):
        for path, text in _walk_text_files(scope):
            for marker in LEAK_MARKERS:
                if marker.lower() in text.lower():
                    report.errors.append(f"answer/verifier leak marker {marker!r} in {path.relative_to(root)}")

    dockerfile = (root / "environment/Dockerfile").read_text(encoding="utf-8")
    if "COPY workspace/ /app/workspace/" not in dockerfile:
        report.errors.append("Dockerfile must copy workspace to /app/workspace")
    if "COPY evidence/ /app/evidence/" not in dockerfile:
        report.errors.append("Dockerfile must copy evidence to /app/evidence")
    if "COPY solution" in dockerfile or "COPY tests" in dockerfile:
        report.errors.append("Agent Dockerfile must not copy solution or tests")

    try:
        harbor_config = tomllib.loads((root / "task.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        report.errors.append(f"invalid Harbor task.toml: {exc}")
    else:
        if harbor_config.get("schema_version") != "1.3":
            report.errors.append("Harbor schema_version must be 1.3")
        if harbor_config.get("artifacts") != ["/app/workspace"]:
            report.errors.append("Harbor must collect /app/workspace for separate verification")
        if harbor_config.get("environment", {}).get("network_mode") != "no-network":
            report.errors.append("Harbor agent environment must use no-network")
        verifier = harbor_config.get("verifier", {})
        if verifier.get("environment_mode") != "separate":
            report.errors.append("Harbor verifier must use a separate environment")
        if verifier.get("network_mode") != "no-network":
            report.errors.append("Harbor verifier environment must use no-network")

    for relative in ("workspace/app.py", "workspace/README.md", "evidence/contract.json", "evidence/cases.json"):
        canonical = root / relative
        build_context = root / "environment" / relative
        if canonical.read_bytes() != build_context.read_bytes():
            report.errors.append(f"Harbor build-context copy is stale: environment/{relative}")

    for path in root.rglob("*"):
        if path.is_symlink():
            resolved = path.resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                report.errors.append(f"escaping symlink: {path.relative_to(root)}")

    return report


def validate_catalog(factory_root: Path, reports: list[ValidationReport]) -> list[str]:
    errors: list[str] = []
    catalog = json.loads((factory_root / "catalog.json").read_text(encoding="utf-8"))
    tasks = catalog.get("tasks", [])
    ids = [task.get("id") for task in tasks]
    if len(ids) != 10 or len(set(ids)) != 10:
        errors.append("catalog must contain 10 unique tasks")
    actual = {report.task_id for report in reports}
    if set(ids) != actual:
        errors.append(f"catalog/task directory mismatch: catalog={sorted(ids)}, actual={sorted(actual)}")
    categories = Counter(task.get("category") for task in tasks)
    if categories and max(categories.values()) / len(tasks) > 0.25:
        errors.append(f"category cap exceeded: {dict(categories)}")

    # A batch must not be ten copies of one omnibus implementation selected by
    # a task-id switch.  Besides looking synthetic, that structure can leak the
    # behavior of sibling private tasks.  Shared harness code is fine; complete
    # solution and verifier artifacts must be task-local and distinct.
    artifact_digests: dict[tuple[str, str], str] = {}
    known_ids = set(ids)
    for task_id in ids:
        task_root = factory_root / "task_families" / task_id
        for relative in ("solution/app.py", "tests/verify.py"):
            path = task_root / relative
            if not path.is_file():
                continue
            payload = path.read_text(encoding="utf-8")
            leaked = sorted(other for other in known_ids - {task_id} if other in payload)
            if leaked:
                errors.append(f"{task_id}/{relative} contains sibling task ids: {leaked}")
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            key = (relative, digest)
            if key in artifact_digests:
                errors.append(f"duplicate {relative}: {artifact_digests[key]} and {task_id}")
            else:
                artifact_digests[key] = task_id
    return errors


def discover_tasks(factory_root: Path) -> list[Path]:
    base = factory_root / "task_families"
    return sorted(path for path in base.iterdir() if path.is_dir() and (path / "task.json").is_file())
