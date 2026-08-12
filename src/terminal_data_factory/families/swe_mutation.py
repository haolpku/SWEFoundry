from __future__ import annotations

import difflib
import json
import subprocess
from pathlib import Path

from .base import read_json_rows
from .production import safe_path


def _patch(before: str, after: str, relative: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{relative}",
        tofile=f"b/{relative}",
    ))


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args], text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def generate_swe_mutations(repo_root: Path, recipes: Path, output: Path) -> list[dict]:
    head = _git(repo_root, "rev-parse", "HEAD")
    if _git(repo_root, "status", "--porcelain"):
        raise ValueError("SWE mutation source checkout must be clean")
    generated = []
    for row in read_json_rows(recipes):
        base_commit = str(row["base_commit"])
        if head != base_commit:
            raise ValueError(f"{row.get('task_id')}: checkout HEAD {head} does not equal base_commit {base_commit}")
        mutation = dict(row["mutation"])
        relative = safe_path(str(mutation["path"]))
        source = repo_root / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        before = source.read_text(encoding="utf-8")
        find = str(mutation["find"])
        replace = str(mutation["replace"])
        occurrences = before.count(find)
        if occurrences != 1:
            raise ValueError(f"{row.get('task_id')}: expected one mutation match, found {occurrences}")
        after = before.replace(find, replace, 1)
        generated.append({
            "instance_id": str(row["task_id"]),
            "repo": str(row["repo_url"]),
            "base_commit": base_commit,
            "problem_statement": str(row["instruction"]),
            "image_name": row.get("image_name"),
            "repo_path": row.get("repo_path", "/testbed"),
            "test_command": str(row["test_command"]),
            "FAIL_TO_PASS": list(row["fail_to_pass"]),
            "PASS_TO_PASS": list(row.get("pass_to_pass", [])),
            "bug_patch": _patch(before, after, relative),
            "patch": _patch(after, before, relative),
            "mutation": {"name": mutation.get("name"), "path": relative},
            "provenance": dict(row.get("provenance", {})),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in generated), encoding="utf-8")
    return generated
