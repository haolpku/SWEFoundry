from __future__ import annotations

import json
import re
import shutil
import tomllib
from pathlib import Path

from ..records import LineageEdge, TaskRecord
from .base import FamilyDescriptor, common_profile, tree_hash


def _task_roots(source: Path) -> list[Path]:
    if (source / "task.toml").is_file():
        return [source]
    return sorted(path.parent for path in source.rglob("task.toml"))


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")


class TerminalBenchFamily:
    descriptor = FamilyDescriptor(
        family_id="terminal-bench",
        task_shape="containerized terminal state transition",
        import_supported=True,
        harbor_native=True,
        generation_tier="P0",
        expert_requirement="low_to_medium",
    )

    def import_records(self, source: Path, *, source_ref: str, dataset_version: str) -> list[TaskRecord]:
        records = []
        for root in _task_roots(source):
            config = tomllib.loads((root / "task.toml").read_text(encoding="utf-8"))
            task = config.get("task", {})
            metadata = config.get("metadata", {})
            instruction = (root / "instruction.md").read_text(encoding="utf-8").strip()
            task_id = str(task.get("name") or root.name)
            artifact_hash = tree_hash(root)
            records.append(TaskRecord(
                task_id=task_id,
                task_version=dataset_version,
                family=self.descriptor.family_id,
                instruction=instruction,
                workspace_kind="filesystem",
                workspace={
                    "source_ref": source_ref,
                    "source_subpath": root.relative_to(source).as_posix() if root != source else ".",
                    "artifact_hash": artifact_hash,
                    "materializer": "harbor_task_directory",
                },
                environment=dict(config.get("environment", {})),
                verifier={
                    **dict(config.get("verifier", {})),
                    "tests_hash": tree_hash(root / "tests") if (root / "tests").is_dir() else None,
                },
                provenance={
                    "source_family": "terminal-bench",
                    "source_ref": source_ref,
                    "authors": task.get("authors", []),
                },
                profile={
                    "objective_type": "terminal",
                    "horizon": metadata.get("horizon", "medium"),
                    "reward_shape": metadata.get("reward_type", "test_fraction"),
                },
                lineage=(LineageEdge("imported_from", artifact_hash),),
            ))
        return records

    def validate_record(self, record: TaskRecord) -> list[str]:
        errors = common_profile(record)
        if record.workspace_kind != "filesystem":
            errors.append(f"{record.task_id}: terminal-bench requires filesystem workspace")
        if not record.verifier.get("tests_hash"):
            errors.append(f"{record.task_id}: terminal-bench requires a tests tree")
        return errors

    def package_for_harbor(self, source: Path, output: Path, *, source_ref: str, dataset_version: str) -> list[Path]:
        records = self.import_records(source, source_ref=source_ref, dataset_version=dataset_version)
        roots = _task_roots(source)
        output.mkdir(parents=True, exist_ok=True)
        destinations = []
        for root, record in zip(roots, records):
            destination = output / _slug(record.task_id)
            if destination.exists():
                raise FileExistsError(f"refusing to overwrite Harbor task: {destination}")
            shutil.copytree(root, destination)
            (destination / "swefoundry-task-record.json").write_text(
                json.dumps(record.as_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            destinations.append(destination)
        return destinations
