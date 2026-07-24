from __future__ import annotations

import json
import os
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_DIRECTORIES = (
    "workspace",
    "environment",
    "generator",
    "solution",
    "tests",
    "anti_cheat",
    "docs",
)
REQUIRED_FILES = (
    "instruction.md",
    "task.toml",
    "task.json",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/Dockerfile",
    "tests/test.sh",
    "anti_cheat/manifest.json",
)
JUNK_NAMES = {".DS_Store", ".pytest_cache", "__pycache__", "build"}
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9]{20,}")


@dataclass
class ReleaseValidationReport:
    task_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def discover_release_tasks(factory_root: Path) -> list[Path]:
    catalog = json.loads((factory_root / "catalog.json").read_text())
    base = factory_root / catalog.get("task_root", "task_families_v3")
    return sorted(
        path
        for path in base.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    )


def _tree_files(root: Path) -> dict[str, bytes]:
    result = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in JUNK_NAMES for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        result[relative.as_posix()] = path.read_bytes()
    return result


def _mutant_entries(mutant: dict) -> list[dict]:
    return mutant.get("files") or [mutant]


def validate_release_task(root: Path) -> ReleaseValidationReport:
    report = ReleaseValidationReport(root.name)
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            report.errors.append(f"missing directory: {relative}")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            report.errors.append(f"missing file: {relative}")
    if report.errors:
        return report

    try:
        config = tomllib.loads((root / "task.toml").read_text())
    except tomllib.TOMLDecodeError as exc:
        report.errors.append(f"invalid task.toml: {exc}")
        return report
    if config.get("schema_version") != "1.3":
        report.errors.append("Harbor schema_version must be 1.3")
    if config.get("artifacts") != ["/app/workspace"]:
        report.errors.append("artifacts must equal ['/app/workspace']")
    if config.get("verifier", {}).get("environment_mode") != "separate":
        report.errors.append("verifier must use a separate environment")
    if config.get("verifier", {}).get("network_mode") != "no-network":
        report.errors.append("verifier must use no-network")
    if config.get("environment", {}).get("network_mode") != "no-network":
        report.errors.append("agent environment must use no-network")
    if config.get("task", {}).get("name") != f"terminal-data-factory/{root.name}":
        report.errors.append("task.name must match the task directory")

    if _tree_files(root / "workspace") != _tree_files(root / "environment/workspace"):
        report.errors.append("workspace and environment/workspace differ")
    for relative in ("solution/solve.sh", "tests/test.sh"):
        if not os.access(root / relative, os.X_OK):
            report.errors.append(f"entry point is not executable: {relative}")

    try:
        manifest = json.loads((root / "anti_cheat/manifest.json").read_text())
    except json.JSONDecodeError as exc:
        report.errors.append(f"invalid mutant manifest: {exc}")
        manifest = {}
    mutants = manifest.get("mutants", [])
    if len(mutants) != 4:
        report.errors.append(f"expected four mutants, got {len(mutants)}")
    for mutant in mutants:
        if not mutant.get("name"):
            report.errors.append("mutant is missing name")
        for entry in _mutant_entries(mutant):
            source = entry.get("source") or entry.get("file")
            destination = entry.get("destination")
            if not source or not destination:
                report.errors.append(
                    f"mutant {mutant.get('name')} lacks source/file or destination"
                )
                continue
            source_path = Path(source)
            if source_path.parts and source_path.parts[0] == "anti_cheat":
                source_path = Path(*source_path.parts[1:])
            if not (root / "anti_cheat" / source_path).is_file():
                report.errors.append(
                    f"mutant {mutant.get('name')} source is missing: {source}"
                )
            if Path(destination).is_absolute() or ".." in Path(destination).parts:
                report.errors.append(
                    f"mutant {mutant.get('name')} has unsafe destination"
                )

    for path in root.rglob("*"):
        if path.name in JUNK_NAMES or path.suffix in {".pyc", ".pyo"}:
            report.errors.append(f"generated residue: {path.relative_to(root)}")
        if path.is_symlink():
            report.errors.append(f"symlink is not allowed: {path.relative_to(root)}")
        if path.is_file() and path.stat().st_size <= 2_000_000:
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            if SECRET_PATTERN.search(text):
                report.errors.append(f"secret-like token in {path.relative_to(root)}")
    test_shell = (root / "tests/test.sh").read_text()
    if "PYTHONPATH=\"$TDF_WORKSPACE\"" in test_shell:
        report.errors.append("verifier process inherits Agent workspace PYTHONPATH")
    dockerfile = (root / "tests/Dockerfile").read_text()
    if re.search(r"(?m)^ENV\\s+PYTHONPATH=/app/workspace\\s*$", dockerfile):
        report.errors.append("verifier image puts Agent workspace on PYTHONPATH")
    return report


def validate_release_catalog(
    factory_root: Path, reports: list[ReleaseValidationReport]
) -> list[str]:
    catalog = json.loads((factory_root / "catalog.json").read_text())
    errors = []
    entries = catalog.get("tasks", [])
    ids = [entry.get("id") for entry in entries]
    if len(ids) != 10 or len(set(ids)) != 10:
        errors.append("catalog must contain ten unique task IDs")
    actual = {report.task_id for report in reports}
    if set(ids) != actual:
        errors.append("catalog and task directory IDs differ")
    categories = Counter(entry.get("category") for entry in entries)
    if categories and max(categories.values()) / len(entries) > 0.2:
        errors.append(f"category share exceeds 20%: {dict(categories)}")
    return errors


def validate_quality_summary(factory_root: Path) -> list[str]:
    path = factory_root / "artifacts/quality-v3-summary.json"
    if not path.is_file():
        return ["missing artifacts/quality-v3-summary.json"]
    summary = json.loads(path.read_text())
    errors = []
    tasks = summary.get("tasks", [])
    if len(tasks) != 10:
        errors.append("quality summary must contain ten tasks")
    if summary.get("summary", {}).get("mutants_rejected") != 40:
        errors.append("quality summary must record forty rejected mutants")
    for task in tasks:
        for field_name in ("audit", "harbor_oracle", "harbor_nop"):
            relative = task.get(field_name)
            if not relative or not (factory_root / relative).is_file():
                errors.append(
                    f"{task.get('id')} quality evidence is missing: {field_name}"
                )
    return errors
