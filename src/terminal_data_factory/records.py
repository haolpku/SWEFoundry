from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SCHEMA_VERSION = "swefoundry-records-v1"
WorkspaceKind = Literal["repo_snapshot", "empty_repo", "oracle_backed", "filesystem"]
RewardStatus = Literal["accept", "accept_recovered", "partial", "reject"]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LineageEdge:
    relation: str
    artifact_hash: str
    parent_task_id: str | None = None


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    task_version: str
    family: str
    instruction: str
    workspace_kind: WorkspaceKind
    workspace: dict[str, Any]
    environment: dict[str, Any]
    verifier: dict[str, Any]
    provenance: dict[str, Any]
    lineage: tuple[LineageEdge, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("task_id", "task_version", "family", "instruction"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        if self.workspace_kind == "repo_snapshot":
            if not self.workspace.get("repo_url") or not self.workspace.get("base_commit"):
                raise ValueError("repo_snapshot requires repo_url and base_commit")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "instruction": self.instruction,
            "workspace_kind": self.workspace_kind,
            "workspace": self.workspace,
            "environment": self.environment,
            "verifier": self.verifier,
        }

    @property
    def task_hash(self) -> str:
        return content_hash(self.identity_payload())

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["task_hash"] = self.task_hash
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskRecord":
        data = dict(value)
        claimed_hash = data.pop("task_hash", None)
        data["lineage"] = tuple(LineageEdge(**item) for item in data.get("lineage", ()))
        record = cls(**data)
        if claimed_hash is not None and claimed_hash != record.task_hash:
            raise ValueError("TaskRecord task_hash does not match its contents")
        return record


@dataclass(frozen=True)
class TrajectoryRecord:
    trajectory_id: str
    task_id: str
    task_version: str
    task_hash: str
    model: str
    agent: str
    attempt: int
    atif_uri: str
    steps: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    wall_time_sec: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TrajectoryRecord":
        return cls(**value)


@dataclass(frozen=True)
class RewardRecord:
    trajectory_id: str
    task_id: str
    task_version: str
    task_hash: str
    reward: float
    status: RewardStatus
    reward_source: Literal["online", "posthoc_artifact", "manual"]
    metrics: dict[str, float | int | bool | None] = field(default_factory=dict)
    failure_tags: tuple[str, ...] = ()
    original_result_hash: str | None = None
    recovery_reason: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not 0.0 <= self.reward <= 1.0:
            raise ValueError("reward must be between 0 and 1")
        if self.status == "accept_recovered" and self.reward_source != "posthoc_artifact":
            raise ValueError("accept_recovered requires posthoc_artifact source")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RewardRecord":
        data = dict(value)
        data["failure_tags"] = tuple(data.get("failure_tags", ()))
        return cls(**data)
