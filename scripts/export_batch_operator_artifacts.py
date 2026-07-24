#!/usr/bin/env python3
"""Export per-task accepted blueprints and contracts from an operator run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from terminal_data_factory.operators.core import atomic_json
from terminal_data_factory.operators.runtime import ArtifactStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    run = json.loads(args.run.read_text())
    store = ArtifactStore(args.store)
    blueprint_digest = run["outputs"]["quality_gate"]["accepted"]
    contract_digest = run["outputs"]["compile_contracts"]["contracts"]
    blueprints = store.get(blueprint_digest).data["blueprints"]
    contracts = {
        item["task_id"]: item
        for item in store.get(contract_digest).data["contracts"]
    }
    if len(blueprints) != 10 or len(contracts) != 10:
        raise SystemExit("operator run must contain exactly ten accepted tasks")
    task_ids = []
    for blueprint in blueprints:
        task_id = blueprint["task_id"]
        if task_id not in contracts:
            raise SystemExit(f"missing contract for {task_id}")
        task_ids.append(task_id)
        atomic_json(args.output / "blueprints" / f"{task_id}.json", blueprint)
        atomic_json(args.output / "contracts" / f"{task_id}.json", contracts[task_id])
    atomic_json(
        args.output / "TASK_INDEX.json",
        {"schema_version": "1.0", "task_count": 10, "task_ids": sorted(task_ids)},
    )
    print(json.dumps({"task_count": 10, "task_ids": sorted(task_ids)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
