from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .batch_qa import scan_task


REPAIR_SCHEMA_VERSION = "1.0"
MAX_SNAPSHOT_BYTES = 1_500_000
MAX_FILE_BYTES = 250_000
MAX_REPAIR_FILES = 40
TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ALLOWED_REPAIR_ROOTS = {
    "environment",
    "steps",
    "verifier",
}
FORBIDDEN_REPAIR_NAMES = {
    "audit-report.json",
    "metadata.json",
    "task.toml",
}


def _safe_relative(value: object) -> PurePosixPath:
    path = PurePosixPath(str(value or ""))
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"unsafe repair path: {path}")
    if path.parts[0] not in ALLOWED_REPAIR_ROOTS:
        raise ValueError(f"repair path outside allowed roots: {path}")
    if path.name in FORBIDDEN_REPAIR_NAMES:
        raise ValueError(f"repair may not replace protected file: {path}")
    return path


def classify_task_failure(task_result: dict[str, Any]) -> dict[str, Any]:
    categories: set[str] = set()
    failed_steps: list[dict[str, Any]] = []
    if not task_result.get("static_validation", {}).get("passed"):
        categories.add("static-contract")
    if not task_result.get("independent_inventory", {}).get("passed"):
        categories.add("inventory-contract")
    if not task_result.get("scan", {}).get("passed"):
        categories.add("sanitation")
    if not task_result.get("audit", {}).get("passed"):
        categories.add("audit-gate")

    for step in task_result.get("progressive_oracle", {}).get("steps", []):
        if step.get("passed"):
            continue
        installs = step.get("installs") or []
        smoke = step.get("public_smoke") or {}
        verifier = step.get("verifier") or {}
        metrics = step.get("metrics") or {}
        text = "\n".join(
            str(value)
            for value in (
                smoke.get("stderr_tail"),
                smoke.get("stdout_tail"),
                verifier.get("stderr_tail"),
                verifier.get("stdout_tail"),
            )
            if value
        )
        failed_checks = step.get("failed_checks") or []
        if failed_checks:
            text = (
                text
                + "\nFAILED CHECK EVIDENCE:\n"
                + json.dumps(failed_checks, ensure_ascii=False, indent=2)
            )
        step_categories: set[str] = set()
        if any(item.get("returncode") != 0 for item in installs):
            step_categories.add("solution-install")
        if any(
            marker in text
            for marker in (
                "SyntaxError",
                "IndentationError",
                "EOL while scanning",
                "unmatched",
            )
        ):
            step_categories.add("syntax-or-escaping")
        if any(
            marker in text
            for marker in (
                "ImportError",
                "ModuleNotFoundError",
                "AttributeError",
                "NameError",
            )
        ):
            step_categories.add("public-contract-runtime")
        if smoke.get("returncode") == 0 and verifier.get("returncode") != 0:
            step_categories.add("hidden-behavior")
        if smoke.get("returncode") != 0:
            step_categories.add("public-smoke")
        if metrics.get("release_pass") != 1:
            step_categories.add("strict-verifier")
        if not step_categories:
            step_categories.add("unknown-runtime")
        categories.update(step_categories)
        failed_steps.append(
            {
                "position": step.get("position"),
                "step": step.get("step"),
                "categories": sorted(step_categories),
                "diagnostic_tail": text[-4000:],
                "failed_checks": failed_checks,
            }
        )

    return {
        "task_id": task_result.get("task_id"),
        "passed": bool(task_result.get("passed")),
        "categories": sorted(categories),
        "failed_steps": failed_steps,
        "repairable": "sanitation" not in categories,
    }


def build_task_snapshot(task: Path) -> dict[str, Any]:
    task = task.resolve()
    scan = scan_task(task)
    if not scan["passed"]:
        raise ValueError(f"{task.name}: refusing to snapshot sensitive task")
    files: list[dict[str, Any]] = []
    total = 0
    for source in sorted(task.rglob("*"), key=lambda item: item.as_posix()):
        if not source.is_file() or source.is_symlink():
            continue
        relative = source.relative_to(task).as_posix()
        if (
            source.suffix.lower() not in TEXT_SUFFIXES
            or source.name == "audit-report.json"
        ):
            continue
        size = source.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValueError(f"{task.name}: snapshot file too large: {relative}")
        text = source.read_text(encoding="utf-8")
        total += len(text.encode("utf-8"))
        if total > MAX_SNAPSHOT_BYTES:
            raise ValueError(f"{task.name}: snapshot exceeds byte budget")
        files.append({"path": relative, "content": text})
    return {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "task_id": task.name,
        "total_bytes": total,
        "files": files,
    }


def validate_repair_payload(
    payload: dict[str, Any],
    *,
    expected_task_id: str,
) -> dict[str, Any]:
    if payload.get("schema_version") != REPAIR_SCHEMA_VERSION:
        raise ValueError("repair schema_version differs")
    if payload.get("task_id") != expected_task_id:
        raise ValueError("repair task_id differs")
    diagnosis = payload.get("diagnosis")
    if not isinstance(diagnosis, str) or not diagnosis.strip():
        raise ValueError("repair diagnosis is required")
    files = payload.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_REPAIR_FILES:
        raise ValueError("repair files must contain 1-40 replacements")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "content",
            "executable",
        }:
            raise ValueError("repair file requires path/content/executable")
        path = _safe_relative(item["path"]).as_posix()
        if path in seen:
            raise ValueError(f"duplicate repair path: {path}")
        seen.add(path)
        content = item["content"]
        if not isinstance(content, str):
            raise ValueError(f"repair content must be text: {path}")
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            raise ValueError(f"repair file exceeds byte budget: {path}")
        if not isinstance(item["executable"], bool):
            raise ValueError(f"repair executable must be boolean: {path}")
        normalized.append(
            {
                "path": path,
                "content": content,
                "executable": item["executable"],
            }
        )
    return {
        **payload,
        "diagnosis": diagnosis.strip(),
        "files": sorted(normalized, key=lambda item: item["path"]),
    }


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for source in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not source.is_file():
            continue
        digest.update(source.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(source.read_bytes())
    return digest.hexdigest()


def apply_repairs_transactionally(
    source_root: Path,
    repairs: dict[str, dict[str, Any]],
    output_root: Path,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise ValueError("repair output must not already exist")
    task_ids = sorted(
        child.name
        for child in source_root.iterdir()
        if child.is_dir() and (child / "task.toml").is_file()
    )
    unknown = sorted(set(repairs) - set(task_ids))
    if unknown:
        raise ValueError(f"repairs target unknown tasks: {unknown}")
    before = _tree_digest(source_root)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.staging-",
            dir=output_root.parent,
        )
    )
    applied: list[dict[str, Any]] = []
    try:
        for child in sorted(source_root.iterdir(), key=lambda item: item.name):
            destination = staging / child.name
            if child.is_dir():
                shutil.copytree(
                    child,
                    destination,
                    ignore=shutil.ignore_patterns(
                        "__pycache__",
                        "*.pyc",
                        "*.pyo",
                    ),
                )
            elif child.is_file():
                shutil.copy2(child, destination)
        for task_id, raw_payload in sorted(repairs.items()):
            payload = validate_repair_payload(
                raw_payload,
                expected_task_id=task_id,
            )
            task_root = staging / task_id
            changed: list[str] = []
            for item in payload["files"]:
                destination = task_root / item["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(item["content"], encoding="utf-8")
                destination.chmod(0o755 if item["executable"] else 0o644)
                changed.append(item["path"])
            applied.append(
                {
                    "task_id": task_id,
                    "diagnosis": payload["diagnosis"],
                    "files": changed,
                }
            )
        os.replace(staging, output_root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "source_digest": before,
        "source_unchanged": before == _tree_digest(source_root),
        "output_digest": _tree_digest(output_root),
        "task_count": len(task_ids),
        "repair_count": len(applied),
        "repairs": applied,
    }


def qa_score(task_result: dict[str, Any]) -> tuple[int, ...]:
    progressive = task_result.get("progressive_oracle", {})
    correctness_micros = sum(
        round(float(step.get("metrics", {}).get("correctness") or 0) * 1_000_000)
        for step in progressive.get("steps", [])
    )
    return (
        int(bool(task_result.get("passed"))),
        int(bool(task_result.get("audit", {}).get("passed"))),
        int(bool(progressive.get("passed"))),
        int(progressive.get("steps_passed") or 0),
        correctness_micros,
        int(bool(task_result.get("independent_inventory", {}).get("passed"))),
        int(bool(task_result.get("static_validation", {}).get("passed"))),
        int(bool(task_result.get("scan", {}).get("passed"))),
    )


def compare_qa_generation(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    before_by_id = {item["task_id"]: item for item in before.get("tasks", [])}
    after_by_id = {item["task_id"]: item for item in after.get("tasks", [])}
    if set(before_by_id) != set(after_by_id):
        raise ValueError("QA task sets differ")
    tasks = []
    for task_id in sorted(before_by_id):
        old_score = qa_score(before_by_id[task_id])
        new_score = qa_score(after_by_id[task_id])
        tasks.append(
            {
                "task_id": task_id,
                "before": list(old_score),
                "after": list(new_score),
                "improved": new_score > old_score,
                "regressed": new_score < old_score,
                "passed": bool(after_by_id[task_id].get("passed")),
            }
        )
    return {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "passed": all(not item["regressed"] for item in tasks),
        "improved": sum(item["improved"] for item in tasks),
        "regressed": sum(item["regressed"] for item in tasks),
        "fully_passed": sum(item["passed"] for item in tasks),
        "tasks": tasks,
    }


def promote_non_regressing_generation(
    before_root: Path,
    after_root: Path,
    before_qa: dict[str, Any],
    after_qa: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    """Promote a repaired task only when independent QA strictly improves it."""
    before_root = before_root.resolve()
    after_root = after_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise ValueError("promotion output must not already exist")
    before_by_id = {item["task_id"]: item for item in before_qa.get("tasks", [])}
    after_by_id = {item["task_id"]: item for item in after_qa.get("tasks", [])}
    if set(before_by_id) != set(after_by_id):
        raise ValueError("QA task sets differ")
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.staging-",
            dir=output_root.parent,
        )
    )
    decisions: list[dict[str, Any]] = []
    try:
        for task_id in sorted(before_by_id):
            old_score = qa_score(before_by_id[task_id])
            new_score = qa_score(after_by_id[task_id])
            promote = new_score > old_score
            source = (after_root if promote else before_root) / task_id
            if not (source / "task.toml").is_file():
                raise ValueError(f"missing task generation: {source}")
            shutil.copytree(
                source,
                staging / task_id,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            decisions.append(
                {
                    "task_id": task_id,
                    "decision": "promote" if promote else "retain",
                    "before": list(old_score),
                    "after": list(new_score),
                }
            )
        os.replace(staging, output_root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "promoted": sum(item["decision"] == "promote" for item in decisions),
        "retained": sum(item["decision"] == "retain" for item in decisions),
        "output_digest": _tree_digest(output_root),
        "decisions": decisions,
    }
