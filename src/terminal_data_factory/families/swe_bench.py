from __future__ import annotations

import json
from pathlib import Path

from ..records import LineageEdge, TaskRecord, content_hash
from .base import FamilyDescriptor, common_profile, read_json_rows


def _test_list(value: object) -> list[str]:
    if isinstance(value, str):
        parsed = json.loads(value)
        return [str(item) for item in parsed]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


class SWEBenchFamily:
    descriptor = FamilyDescriptor(
        family_id="swe-bench",
        task_shape="pinned repository issue resolution",
        import_supported=True,
        harbor_native=False,
        generation_tier="P0",
        expert_requirement="low_for_mutation_medium_for_real_issues",
    )

    def import_records(self, source: Path, *, source_ref: str, dataset_version: str) -> list[TaskRecord]:
        records = []
        for row in read_json_rows(source):
            task_id = str(row.get("instance_id") or row.get("task_id") or "")
            repo = str(row.get("repo") or row.get("repo_url") or "")
            repo_url = repo if "://" in repo else f"https://github.com/{repo}"
            base_commit = str(row.get("base_commit") or "")
            instruction = str(row.get("problem_statement") or row.get("instruction") or "").strip()
            artifact_hash = content_hash(row)
            records.append(TaskRecord(
                task_id=task_id,
                task_version=dataset_version,
                family=self.descriptor.family_id,
                instruction=instruction,
                workspace_kind="repo_snapshot",
                workspace={"repo_url": repo_url, "base_commit": base_commit, "materializer": "swe_bench"},
                environment={
                    "image": row.get("image_name"),
                    "version": row.get("version"),
                    "network_mode": "no-network",
                },
                verifier={
                    "adapter": "swe_bench",
                    "fail_to_pass": _test_list(row.get("FAIL_TO_PASS", [])),
                    "pass_to_pass": _test_list(row.get("PASS_TO_PASS", [])),
                },
                provenance={"source_family": "swe-bench", "source_ref": source_ref},
                profile={"objective_type": "repo_repair", "horizon": "medium", "reward_shape": "test_fraction"},
                lineage=(LineageEdge("imported_from", artifact_hash),),
            ))
        return records

    def validate_record(self, record: TaskRecord) -> list[str]:
        errors = common_profile(record)
        if record.workspace_kind != "repo_snapshot":
            errors.append(f"{record.task_id}: swe-bench requires repo_snapshot workspace")
        if not record.verifier.get("fail_to_pass"):
            errors.append(f"{record.task_id}: swe-bench requires FAIL_TO_PASS tests")
        return errors

    def package_for_harbor(self, source: Path, output: Path, *, source_ref: str, dataset_version: str) -> list[Path]:
        raise NotImplementedError("swe-bench Harbor packaging requires the pinned image/runtime adapter")
