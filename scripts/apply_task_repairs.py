#!/usr/bin/env python3
"""Apply validated task repair payloads to a new immutable generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from terminal_data_factory.operators.core import atomic_json
from terminal_data_factory.repair import apply_repairs_transactionally


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks-root", type=Path, required=True)
    parser.add_argument("--repairs-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    repairs = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.repairs_root.glob("*/repair.json"))
    }
    if not repairs:
        raise SystemExit("no repair payloads found")
    result = apply_repairs_transactionally(
        args.tasks_root,
        repairs,
        args.output_root,
    )
    atomic_json(args.evidence, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
