from __future__ import annotations

from pathlib import Path

from ..records import LineageEdge, TaskRecord, content_hash
from .base import FamilyDescriptor, common_profile, read_json_rows
from .production import compile_harbor_task, spec_from_recipe


def _production_row(row: dict, *, source_ref: str, dataset_version: str) -> dict:
    provenance = dict(row.get("provenance", {}))
    run_ids = [provenance.get(name) for name in ("contract_run_id", "solution_run_id", "verifier_run_id")]
    if any(not value for value in run_ids) or len(set(run_ids)) != 3:
        raise ValueError(
            f"{row.get('task_id')}: contract_run_id, solution_run_id, and verifier_run_id must be non-empty and distinct"
        )
    if not row.get("contract"):
        raise ValueError(f"{row.get('task_id')}: contract is required")
    value = dict(row)
    value["family"] = "nl2repo"
    value["solution_files"] = row.get("reference_files", row.get("solution_files", {}))
    value["verifier_files"] = row.get("hidden_test_files", row.get("verifier_files", {}))
    value["horizon"] = row.get("horizon", "long")
    value["provenance"] = {
        **provenance,
        "source_ref": source_ref,
        "dataset_version": dataset_version,
        "contract": row["contract"],
    }
    return value


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
        tasks = []
        for row in read_json_rows(source):
            tasks.append(compile_harbor_task(
                spec_from_recipe(_production_row(row, source_ref=source_ref, dataset_version=dataset_version), expected_family="nl2repo"),
                output,
            ))
        return tasks
