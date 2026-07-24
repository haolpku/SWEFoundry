from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def stable_seed(family_id: str, ordinal: int) -> int:
    payload = f"terminal-data-factory:v1:{family_id}:{ordinal}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & 0x7FFF_FFFF


def create_plan(factory_root: Path, instances: int, rollouts: int, shard_size: int, output: Path) -> dict[str, Any]:
    if instances <= 0 or rollouts <= 0 or shard_size <= 0:
        raise ValueError("instances, rollouts, and shard_size must be positive")
    catalog = json.loads((factory_root / "catalog.json").read_text(encoding="utf-8"))
    families = sorted(catalog["tasks"], key=lambda item: (item["order"], item["id"]))
    task_root = factory_root / catalog.get("task_root", "task_families_v3")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "instances.jsonl"
    category_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    with manifest_path.open("w", encoding="utf-8") as handle:
        for ordinal in range(instances):
            family = families[ordinal % len(families)]
            family_id = family["id"]
            variation = ordinal // len(families)
            seed = stable_seed(family_id, variation)
            category_counts[family["category"]] += 1
            family_counts[family_id] += 1
            record = {
                "schema_version": "1.0",
                "instance_id": f"{family_id}-{variation:06d}",
                "family_id": family_id,
                "category": family["category"],
                "seed": seed,
                "task_id": family["id"],
                "family_revision": 1,
                "generator": str((task_root / family["id"] / "generator").resolve()),
                "task_dir": str((task_root / family["id"]).resolve()),
                "runner": {
                    "name": "harbor",
                    "task_name": f"terminal-data-factory/{family_id}",
                    "environment_import_path": "harbor_ext.static_no_network:StaticNoNetworkDockerEnvironment",
                },
                "rollouts_required": rollouts,
                "release_gate": "human-approved",
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    total_trials = instances * rollouts
    shards = []
    for start in range(0, total_trials, shard_size):
        stop = min(start + shard_size, total_trials)
        shards.append({"shard_id": f"trial-{start // shard_size:05d}", "start": start, "stop": stop, "trials": stop - start})
    summary = {
        "schema_version": "1.0",
        "instances": instances,
        "rollouts_per_instance": rollouts,
        "total_trials": total_trials,
        "shard_size": shard_size,
        "shards": shards,
        "family_counts": dict(sorted(family_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "max_category_share": max(category_counts.values()) / instances,
        "artifact_contract": ["task.json", "agent-trajectory.json", "runtime-events.jsonl", "reward.txt", "ctrf.json", "failure-labels.json", "qa.json"],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output / "shards.jsonl").open("w", encoding="utf-8") as handle:
        for shard in shards:
            handle.write(json.dumps(shard, sort_keys=True) + "\n")
    return summary
