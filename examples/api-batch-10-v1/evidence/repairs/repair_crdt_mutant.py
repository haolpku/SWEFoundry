#!/usr/bin/env python3
"""Make the CRDT Step-3 false-positive probe deterministic and observable."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TASK_ID = "mini-crdt-notebook-engine"
MUTANT_PATH = "verifier/anti_cheat/fp3_input_order_concurrency.py"


MUTANT = """#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import py_compile

ROOT = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
ENGINE = ROOT / 'environment' / 'codebase' / 'crdtnotebook' / 'engine.py'
PATTERN = '''        children[key].sort()
'''
REPLACEMENT = '''        children[key].sort(reverse=True)
'''
text = ENGINE.read_text(encoding='utf-8')
if PATTERN not in text:
    raise SystemExit('fp3 exact Oracle pattern not found')
ENGINE.write_text(text.replace(PATTERN, REPLACEMENT, 1), encoding='utf-8')
py_compile.compile(str(ENGINE), doraise=True)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fragment", type=Path)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.fragment.read_text(encoding="utf-8"))
    if payload.get("task_id") != TASK_ID or payload.get("fragment") != "verification":
        raise SystemExit("refusing to repair an unexpected fragment")
    matches = [item for item in payload["files"] if item["path"] == MUTANT_PATH]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one {MUTANT_PATH}")
    matches[0]["content"] = MUTANT
    note = (
        "Repair: Step 3 mutant deterministically reverses the canonical sibling "
        "ordering, guaranteeing an observable failure for concurrent inserts."
    )
    notes = payload.setdefault("implementation_notes", [])
    if note not in notes:
        notes.append(note)
    args.fragment.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    record = {
        "task_id": TASK_ID,
        "kind": "semantic-mutant-repair",
        "path": MUTANT_PATH,
        "reason": (
            "The generated input-order mutant was observationally inert because "
            "parse_notebook_ops canonicalizes input before merge_notebook_text."
        ),
        "change": (
            "Replace canonical sibling sorting with deterministic reverse sorting; "
            "the disclosed concurrent-insert check must reject it."
        ),
    }
    args.record.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
