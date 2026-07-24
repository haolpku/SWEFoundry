#!/usr/bin/env python3
"""Compare immutable QA generations and reject aggregate regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from terminal_data_factory.operators.core import atomic_json
from terminal_data_factory.repair import compare_qa_generation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    comparison = compare_qa_generation(
        json.loads(args.before.read_text(encoding="utf-8")),
        json.loads(args.after.read_text(encoding="utf-8")),
    )
    atomic_json(args.output, comparison)
    print(json.dumps(comparison, indent=2, sort_keys=True))
    return 0 if comparison["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
