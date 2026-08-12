from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from .records import RewardRecord


@dataclass(frozen=True)
class DifficultyCalibration:
    task_id: str
    task_version: str
    task_hash: str
    attempts: int
    full_pass_rate: float
    mean_reward: float
    label: str
    model_pass_rates: dict[str, float]

    def as_dict(self) -> dict:
        return asdict(self)


def _label(full_pass_rate: float, mean_reward: float) -> str:
    if full_pass_rate >= 0.9:
        return "trivial"
    if full_pass_rate >= 0.6:
        return "easy"
    if full_pass_rate >= 0.2:
        return "medium"
    if full_pass_rate > 0 or mean_reward >= 0.25:
        return "hard"
    return "frontier_or_broken"


def calibrate(rewards: list[RewardRecord], trajectory_models: dict[str, str]) -> list[DifficultyCalibration]:
    by_task: dict[tuple[str, str, str], list[RewardRecord]] = defaultdict(list)
    for reward in rewards:
        by_task[(reward.task_id, reward.task_version, reward.task_hash)].append(reward)
    output = []
    for (task_id, task_version, task_hash), items in sorted(by_task.items()):
        model_values: dict[str, list[float]] = defaultdict(list)
        for item in items:
            model_values[trajectory_models.get(item.trajectory_id, "unknown")].append(item.reward)
        pass_rate = sum(item.reward == 1.0 for item in items) / len(items)
        mean_reward = sum(item.reward for item in items) / len(items)
        output.append(DifficultyCalibration(
            task_id=task_id,
            task_version=task_version,
            task_hash=task_hash,
            attempts=len(items),
            full_pass_rate=pass_rate,
            mean_reward=mean_reward,
            label=_label(pass_rate, mean_reward),
            model_pass_rates={model: sum(v == 1.0 for v in values) / len(values) for model, values in sorted(model_values.items())},
        ))
    return output
