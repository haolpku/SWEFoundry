#!/usr/bin/env python3
"""Validate and safely materialize one model-produced task bundle."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from merge_model_fragments import validate_task_id


SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(
        r"(?i)(?:api[_-]?key|bearer)\s*[:=]\s*"
        r"['\"]?(?!<REDACTED)[A-Za-z0-9._-]{16,}"
    ),
    re.compile(
        r"(?i)\bauthorization\s*[:=]\s*['\"]?bearer\s+"
        r"(?!<REDACTED)[A-Za-z0-9._-]{16,}"
    ),
)
PRIVATE_ENDPOINT = re.compile(
    r"https?://(?:localhost|127(?:\.\d{1,3}){3}|10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|"
    r"(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?",
    re.IGNORECASE,
)
HOST_PATH = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[^/\s\"']+")
STEP_ROOT = re.compile(r"^[1-5](?:-|$)")


@dataclass(frozen=True)
class MaterializedFile:
    relative: PurePosixPath
    executable: bool
    content: str


@dataclass(frozen=True)
class ValidatedBundle:
    task_id: str
    files: tuple[MaterializedFile, ...]
    known_open_gates: tuple[str, ...]


def _unsafe_content(content: str) -> str | None:
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        return "secret-like content"
    if PRIVATE_ENDPOINT.search(content):
        return "private or IP endpoint"
    if HOST_PATH.search(content):
        return "host absolute path"
    return None


def validate_bundle(
    payload: dict,
    *,
    expected_task_id: str | None = None,
) -> ValidatedBundle:
    envelope_reason = _unsafe_content(
        json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )
    if envelope_reason:
        raise ValueError(f"{envelope_reason}: bundle envelope")
    if payload.get("schema_version") != "1.0":
        raise ValueError("bundle schema_version must be 1.0")
    task_id = validate_task_id(payload.get("task_id"))
    if expected_task_id is not None and task_id != validate_task_id(expected_task_id):
        raise ValueError(f"unexpected task id: {task_id!r}")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("bundle files must be non-empty")

    seen: set[str] = set()
    normalized: list[MaterializedFile] = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "executable",
            "content",
        }:
            raise ValueError("every file must have only path/executable/content")
        relative = PurePosixPath(str(item["path"]))
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or relative.as_posix() in {"", "."}
        ):
            raise ValueError(f"unsafe path: {relative}")
        rendered = relative.as_posix()
        if rendered in seen:
            raise ValueError(f"duplicate path: {rendered}")
        seen.add(rendered)
        content = item["content"]
        if not isinstance(content, str):
            raise ValueError(f"non-string content: {rendered}")
        reason = _unsafe_content(content)
        if reason:
            raise ValueError(f"{reason}: {rendered}")
        if not isinstance(item["executable"], bool):
            raise ValueError(f"executable must be boolean: {rendered}")
        normalized.append(MaterializedFile(relative, item["executable"], content))

    required = {
        "README.md",
        "metadata.json",
        "task.toml",
        "environment/Dockerfile",
        "environment/knowledge/index.md",
        "environment/knowledge/public_api.md",
        "environment/knowledge/public_api.json",
        "verifier/run_audit.py",
    }
    missing = required - seen
    if missing:
        raise ValueError(f"bundle missing required files: {sorted(missing)}")

    step_roots = {
        path.relative.parts[1]
        for path in normalized
        if len(path.relative.parts) >= 3 and path.relative.parts[0] == "steps"
    }
    if len(step_roots) != 5 or any(not STEP_ROOT.match(root) for root in step_roots):
        raise ValueError(f"expected numbered step roots 1-5, got {sorted(step_roots)}")
    step_numbers = {int(root[0]) for root in step_roots}
    if step_numbers != set(range(1, 6)):
        raise ValueError(f"expected steps 1-5, got {sorted(step_numbers)}")
    for root in step_roots:
        required_step_files = {
            f"steps/{root}/instruction.md",
            f"steps/{root}/solution/solve.sh",
            f"steps/{root}/tests/verifier.py",
            f"steps/{root}/tests/test.sh",
        }
        missing_step = required_step_files - seen
        if missing_step:
            raise ValueError(
                f"step {root} missing required files: {sorted(missing_step)}"
            )

    mutant_paths = [
        item.relative
        for item in normalized
        if item.relative.parts[:2] == ("verifier", "anti_cheat")
        and item.relative.suffix == ".py"
    ]
    if len(mutant_paths) != 5:
        raise ValueError(f"expected five Python mutants, got {len(mutant_paths)}")
    covered_steps: set[int] = set()
    for path in mutant_paths:
        match = re.search(r"(?:fp|step)[_-]?([1-5])", path.stem, re.IGNORECASE)
        if not match:
            raise ValueError(f"mutant filename does not identify step 1-5: {path}")
        covered_steps.add(int(match.group(1)))
    if covered_steps != set(range(1, 6)):
        raise ValueError(
            f"mutants must cover every step 1-5, got {sorted(covered_steps)}"
        )

    return ValidatedBundle(
        task_id,
        tuple(normalized),
        tuple(str(item) for item in payload.get("known_open_gates", [])),
    )


def load_and_validate_bundle(
    path: Path,
    *,
    expected_task_id: str | None = None,
) -> ValidatedBundle:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("```"):
        raise ValueError("bundle contains Markdown fences")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("bundle root must be an object")
    return validate_bundle(payload, expected_task_id=expected_task_id)


def materialize_bundle(bundle: ValidatedBundle, output: Path) -> None:
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("output directory must be absent or empty")
    output.mkdir(parents=True, exist_ok=True)
    for item in bundle.files:
        destination = output.joinpath(*item.relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(item.content.rstrip() + "\n", encoding="utf-8")
        if item.executable:
            os.chmod(destination, 0o755)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-id")
    args = parser.parse_args()

    try:
        bundle = load_and_validate_bundle(
            args.bundle, expected_task_id=args.task_id
        )
        materialize_bundle(bundle, args.output)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "task_id": bundle.task_id,
                "file_count": len(bundle.files),
                "known_open_gates": list(bundle.known_open_gates),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
