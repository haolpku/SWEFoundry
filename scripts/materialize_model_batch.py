#!/usr/bin/env python3
"""Transactionally validate and materialize a non-overlapping task batch."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from materialize_model_bundle import load_and_validate_bundle, materialize_bundle


def materialize_batch(
    bundle_paths: list[Path],
    output: Path,
    *,
    expected_count: int = 10,
) -> dict:
    if len(bundle_paths) != expected_count:
        raise ValueError(
            f"expected {expected_count} bundles, received {len(bundle_paths)}"
        )
    bundles = [load_and_validate_bundle(path) for path in bundle_paths]
    task_ids = [bundle.task_id for bundle in bundles]
    if len(set(task_ids)) != len(task_ids):
        duplicates = sorted(
            task_id for task_id in set(task_ids) if task_ids.count(task_id) > 1
        )
        raise ValueError(f"duplicate task ids in batch: {duplicates}")
    if output.exists():
        raise ValueError("batch output must not already exist")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    try:
        for bundle in bundles:
            materialize_bundle(bundle, staging / bundle.task_id)
        manifest = {
            "schema_version": "1.0",
            "task_count": len(bundles),
            "task_ids": sorted(task_ids),
            "files_per_task": {
                bundle.task_id: len(bundle.files) for bundle in bundles
            },
        }
        (staging / "BATCH_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=10)
    args = parser.parse_args()
    try:
        manifest = materialize_batch(
            args.bundle, args.output, expected_count=args.expected_count
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({**manifest, "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
