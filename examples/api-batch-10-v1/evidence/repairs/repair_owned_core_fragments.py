#!/usr/bin/env python3
"""Repair solution scripts that incorrectly locate files under the workspace."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


OWNED_TASKS = {
    "mini-wasm-module-auditor",
    "mini-png-asset-pipeline",
    "mini-mqtt-session-broker",
}
BAD_SOURCE = re.compile(
    r'^SRC="\$ROOT/steps/[1-5]-[^"]+/solution/files/([^"]+)"$',
    re.MULTILINE,
)


def repair(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    task_id = payload.get("task_id")
    if task_id not in OWNED_TASKS:
        raise ValueError(f"refusing to edit unowned task: {task_id!r}")
    if payload.get("fragment") != "core":
        raise ValueError("expected a core fragment")
    changes = []
    for item in payload.get("files", []):
        if not item.get("path", "").endswith("/solution/solve.sh"):
            continue
        match = BAD_SOURCE.search(item["content"])
        if not match:
            continue
        replacement = (
            'SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
            f'SRC="$SCRIPT_DIR/files/{match.group(1)}"'
        )
        item["content"] = BAD_SOURCE.sub(replacement, item["content"], count=1)
        changes.append(f"made solution source task-relative in {item['path']}")
    note = (
        "Infra repair: solution scripts locate immutable payloads relative to "
        "their own script while TDF_WORKSPACE selects only the destination."
    )
    notes = payload.setdefault("implementation_notes", [])
    if changes and note not in notes:
        notes.append(note)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return {"task_id": task_id, "changes": changes}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fragment", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    result = repair(args.fragment)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
