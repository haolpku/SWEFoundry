from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from ..records import TaskRecord


@dataclass(frozen=True)
class FamilyDescriptor:
    family_id: str
    task_shape: str
    import_supported: bool
    harbor_native: bool
    generation_tier: str
    expert_requirement: str

    def as_dict(self) -> dict:
        return {
            "family_id": self.family_id,
            "task_shape": self.task_shape,
            "import_supported": self.import_supported,
            "harbor_native": self.harbor_native,
            "generation_tier": self.generation_tier,
            "expert_requirement": self.expert_requirement,
        }


class TaskFamily(Protocol):
    descriptor: FamilyDescriptor

    def import_records(
        self,
        source: Path,
        *,
        source_ref: str,
        dataset_version: str,
    ) -> list[TaskRecord]: ...

    def validate_record(self, record: TaskRecord) -> list[str]: ...

    def package_for_harbor(
        self,
        source: Path,
        output: Path,
        *,
        source_ref: str,
        dataset_version: str,
    ) -> list[Path]: ...


def read_json_rows(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return value
    for key in ("tasks", "instances", "records"):
        if isinstance(value.get(key), list):
            return value[key]
    return [value]


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def write_jsonl(records: Iterable[TaskRecord], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def common_profile(record: TaskRecord) -> list[str]:
    errors = []
    if record.profile.get("horizon") not in {"short", "medium", "long", "ultra_long"}:
        errors.append(f"{record.task_id}: missing or invalid profile.horizon")
    if not record.profile.get("objective_type"):
        errors.append(f"{record.task_id}: missing profile.objective_type")
    if not record.profile.get("reward_shape"):
        errors.append(f"{record.task_id}: missing profile.reward_shape")
    return errors
