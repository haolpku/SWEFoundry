#!/usr/bin/env python3
"""Merge independently generated task fragments into one materializable bundle."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Iterable

from terminal_data_factory.operators.core import atomic_json


TASK_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEFAULT_FRAGMENTS = ("core", "verification", "package")


def validate_task_id(value: object) -> str:
    task_id = str(value or "")
    if not TASK_ID.fullmatch(task_id):
        raise ValueError(
            f"unsafe task_id {task_id!r}; expected lowercase kebab-case"
        )
    return task_id


def _safe_relative_path(value: object) -> str:
    path = PurePosixPath(str(value or ""))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe file path: {path}")
    return path.as_posix()


def merge_fragments(
    paths: Iterable[Path],
    *,
    expected_task_id: str | None = None,
    expected_fragments: Iterable[str] = DEFAULT_FRAGMENTS,
) -> dict:
    """Validate and merge fragments for exactly one task.

    Model workers may run concurrently, but they cannot silently cross task
    boundaries or overwrite a path produced by another worker.
    """

    expected_task_id = (
        validate_task_id(expected_task_id) if expected_task_id is not None else None
    )
    files: list[dict] = []
    notes: list[str] = []
    gates: list[str] = []
    seen_paths: set[str] = set()
    fragment_names: list[str] = []
    task_id: str | None = expected_task_id

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0":
            raise ValueError(f"{path}: invalid schema version")
        fragment_task_id = validate_task_id(payload.get("task_id"))
        if task_id is None:
            task_id = fragment_task_id
        if fragment_task_id != task_id:
            raise ValueError(
                f"{path}: task_id {fragment_task_id!r} does not match {task_id!r}"
            )
        fragment = str(payload.get("fragment") or "")
        if not fragment:
            raise ValueError(f"{path}: missing fragment name")
        if fragment in fragment_names:
            raise ValueError(f"duplicate fragment name: {fragment}")
        fragment_names.append(fragment)

        fragment_files = payload.get("files")
        if not isinstance(fragment_files, list):
            raise ValueError(f"{path}: files must be a list")
        for item in fragment_files:
            if not isinstance(item, dict):
                raise ValueError(f"{path}: every file must be an object")
            item_path = _safe_relative_path(item.get("path"))
            if item_path in seen_paths:
                raise ValueError(f"duplicate file across fragments: {item_path}")
            seen_paths.add(item_path)
            files.append({**item, "path": item_path})
        notes.extend(str(item) for item in payload.get("implementation_notes", []))
        gates.extend(str(item) for item in payload.get("known_open_gates", []))

    if task_id is None:
        raise ValueError("at least one fragment is required")
    expected = set(expected_fragments)
    actual = set(fragment_names)
    if actual != expected:
        raise ValueError(
            f"fragments differ: expected={sorted(expected)}, got={sorted(actual)}"
        )
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "files": sorted(files, key=lambda item: item["path"]),
        "implementation_notes": notes,
        "known_open_gates": gates,
        "fragments": sorted(fragment_names),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragment", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-id")
    parser.add_argument(
        "--expected-fragment",
        action="append",
        help="repeat to override the expected core/verification/package set",
    )
    args = parser.parse_args()

    try:
        bundle = merge_fragments(
            args.fragment,
            expected_task_id=args.task_id,
            expected_fragments=args.expected_fragment or DEFAULT_FRAGMENTS,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    atomic_json(args.output, bundle)
    print(
        json.dumps(
            {
                "task_id": bundle["task_id"],
                "file_count": len(bundle["files"]),
                "known_open_gates": bundle["known_open_gates"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
