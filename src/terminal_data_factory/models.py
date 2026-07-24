from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskFamily:
    root: Path
    raw: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.raw["id"])

    @property
    def category(self) -> str:
        return str(self.raw["category"])

    @property
    def status(self) -> str:
        return str(self.raw["status"])

    @property
    def instruction_path(self) -> Path:
        return self.root / str(self.raw["instruction"])

    @classmethod
    def load(cls, root: Path) -> "TaskFamily":
        manifest = root / "task.json"
        return cls(root=root, raw=json.loads(manifest.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class AuditResult:
    task_id: str
    unsolved_score: float | None
    oracle_score: float | None
    anti_cheat_scores: dict[str, float]
    passed: bool
    errors: tuple[str, ...] = ()
    reproducible: bool | None = None
    seed_sensitive: bool | None = None
    published_evidence_matches: bool | None = None
    behavioral_tests: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "unsolved_score": self.unsolved_score,
            "oracle_score": self.oracle_score,
            "anti_cheat_scores": self.anti_cheat_scores,
            "passed": self.passed,
            "errors": list(self.errors),
            "reproducible": self.reproducible,
            "seed_sensitive": self.seed_sensitive,
            "published_evidence_matches": self.published_evidence_matches,
            "behavioral_tests": self.behavioral_tests,
        }
