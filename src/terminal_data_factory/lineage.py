from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from .records import TaskRecord, content_hash


def normalized_instruction(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold())


def exact_duplicate_groups(records: list[TaskRecord]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        groups[record.task_hash].append(record.task_id)
    return [sorted(ids) for ids in groups.values() if len(ids) > 1]


def query_duplicate_groups(records: list[TaskRecord]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        groups[content_hash(normalized_instruction(record.instruction))].append(record.task_id)
    return [sorted(ids) for ids in groups.values() if len(ids) > 1]


def validate_lineage(records: list[TaskRecord]) -> list[str]:
    errors: list[str] = []
    by_id = {record.task_id: record for record in records}
    for record in records:
        for edge in record.lineage:
            if edge.parent_task_id and edge.parent_task_id not in by_id:
                errors.append(f"{record.task_id}: missing parent {edge.parent_task_id}")
            if not edge.artifact_hash.startswith("sha256:"):
                errors.append(f"{record.task_id}: invalid lineage artifact hash")
    return errors


def load_task_records(path: Path) -> list[TaskRecord]:
    return [TaskRecord.from_dict(json.loads(line)) for line in path.read_text().splitlines() if line]
