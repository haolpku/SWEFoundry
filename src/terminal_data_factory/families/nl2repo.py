from __future__ import annotations

from pathlib import Path

from ..records import LineageEdge, TaskRecord, content_hash
from .base import FamilyDescriptor, common_profile, read_json_rows


class NL2RepoFamily:
    descriptor = FamilyDescriptor(
        family_id="nl2repo",
        task_shape="natural-language contract to new repository",
        import_supported=True,
        harbor_native=False,
        generation_tier="P0",
        expert_requirement="low_with_independent_behavioral_tests",
    )

    def import_records(self, source: Path, *, source_ref: str, dataset_version: str) -> list[TaskRecord]:
        records = []
        for row in read_json_rows(source):
            task_id = str(row.get("task_id") or row.get("id") or "")
            instruction = str(row.get("instruction") or row.get("requirements") or "").strip()
            artifact_hash = content_hash(row)
            records.append(TaskRecord(
                task_id=task_id,
                task_version=dataset_version,
                family=self.descriptor.family_id,
                instruction=instruction,
                workspace_kind="empty_repo",
                workspace={
                    "source_ref": source_ref,
                    "starter_uri": row.get("starter_uri"),
                    "materializer": "empty_repo",
                },
                environment={**dict(row.get("environment", {})), "language": row.get("language")},
                verifier={**dict(row.get("verifier", {})), "contract": row.get("contract", {})},
                provenance={"source_family": "nl2repo", "source_ref": source_ref},
                profile={
                    "objective_type": "repo_generation",
                    "horizon": row.get("horizon", "long"),
                    "reward_shape": row.get("reward_shape", "test_fraction"),
                },
                lineage=(LineageEdge("imported_from", artifact_hash),),
            ))
        return records

    def validate_record(self, record: TaskRecord) -> list[str]:
        errors = common_profile(record)
        if record.workspace_kind != "empty_repo":
            errors.append(f"{record.task_id}: nl2repo requires empty_repo workspace")
        if not record.verifier.get("contract") and not record.verifier.get("hidden_tests_hash"):
            errors.append(f"{record.task_id}: nl2repo requires a behavioral contract or hidden tests")
        return errors

    def package_for_harbor(self, source: Path, output: Path, *, source_ref: str, dataset_version: str) -> list[Path]:
        raise NotImplementedError("nl2repo Harbor packaging requires materialized environment and tests artifacts")
