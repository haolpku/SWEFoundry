from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .records import RewardRecord


RECOVERABLE_EXCEPTIONS = {"RewardFileNotFoundError"}


def _load_scalar(path: Path) -> float:
    return float(path.read_text(encoding="utf-8").strip())


def _structured_score(value: dict[str, Any]) -> float | None:
    for key in ("reward", "score", "weighted_total"):
        if isinstance(value.get(key), (int, float)):
            return float(value[key])
    return None


def recover_trial(trial_dir: Path, *, task_id: str, task_version: str, task_hash: str) -> RewardRecord | None:
    result_path = trial_dir / "result.json"
    reward_txt = trial_dir / "verifier/reward.txt"
    reward_json = trial_dir / "verifier/reward.json"
    if not result_path.is_file() or not reward_txt.is_file() or not reward_json.is_file():
        return None
    result_raw = result_path.read_bytes()
    result = json.loads(result_raw)
    exception = result.get("exception_info") or {}
    if exception.get("exception_type") not in RECOVERABLE_EXCEPTIONS:
        return None
    structured = json.loads(reward_json.read_text(encoding="utf-8"))
    scalar = _load_scalar(reward_txt)
    structured_score = _structured_score(structured)
    if structured_score is None or abs(scalar - structured_score) > 1e-9 or not 0 <= scalar <= 1:
        return None
    if structured.get("compliance") is False or structured.get("anti_hack") is False:
        return None
    trajectory_id = str(result.get("trajectory_id") or result.get("id") or trial_dir.name)
    status = "accept_recovered" if scalar == 1.0 else ("partial" if scalar >= 0.5 else "reject")
    return RewardRecord(
        trajectory_id=trajectory_id,
        task_id=task_id,
        task_version=task_version,
        task_hash=task_hash,
        reward=scalar,
        status=status,
        reward_source="posthoc_artifact",
        metrics={key: value for key, value in structured.items() if isinstance(value, (int, float, bool))},
        original_result_hash="sha256:" + hashlib.sha256(result_raw).hexdigest(),
        recovery_reason="delayed_reward_visibility",
    )
