#!/usr/bin/env python3
"""Build the next immutable generation using only QA-improving repairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from terminal_data_factory.operators.core import atomic_json
from terminal_data_factory.repair import promote_non_regressing_generation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-root", type=Path, required=True)
    parser.add_argument("--after-root", type=Path, required=True)
    parser.add_argument("--before-qa", type=Path, required=True)
    parser.add_argument("--after-qa", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    result = promote_non_regressing_generation(
        args.before_root,
        args.after_root,
        json.loads(args.before_qa.read_text(encoding="utf-8")),
        json.loads(args.after_qa.read_text(encoding="utf-8")),
        args.output_root,
    )
    atomic_json(args.evidence, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
