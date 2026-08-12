from __future__ import annotations

import json
from pathlib import Path

import pytest

from terminal_data_factory.calibration import calibrate
from terminal_data_factory.hf_export import export_jsonl_shards
from terminal_data_factory.lineage import exact_duplicate_groups, query_duplicate_groups
from terminal_data_factory.mutants import MutationRule, generate_mutants
from terminal_data_factory.records import RewardRecord, TaskRecord, TrajectoryRecord, content_hash
from terminal_data_factory.recovery import recover_trial


def task(task_id: str = "task-1", instruction: str = "Fix the ledger") -> TaskRecord:
    return TaskRecord(
        task_id=task_id,
        task_version="1.0.0",
        family="synthetic-repair",
        instruction=instruction,
        workspace_kind="repo_snapshot",
        workspace={"repo_url": "https://example.invalid/repo", "base_commit": "abc"},
        environment={"image_digest": "sha256:image", "network_mode": "no-network"},
        verifier={"version": "1", "hidden_tests_hash": "sha256:tests"},
        provenance={"generation_method": "test"},
    )


def test_task_hash_round_trip_and_tamper_detection() -> None:
    original = task()
    restored = TaskRecord.from_dict(original.as_dict())
    assert restored.task_hash == original.task_hash
    damaged = original.as_dict()
    damaged["instruction"] = "different"
    with pytest.raises(ValueError, match="task_hash"):
        TaskRecord.from_dict(damaged)


def test_empty_profile_preserves_pre_v03_task_hash() -> None:
    original = task()
    legacy_identity = {
        "instruction": original.instruction,
        "workspace_kind": original.workspace_kind,
        "workspace": original.workspace,
        "environment": original.environment,
        "verifier": original.verifier,
    }
    payload = original.as_dict()
    payload.pop("profile")
    payload["task_hash"] = content_hash(legacy_identity)
    assert TaskRecord.from_dict(payload).task_hash == payload["task_hash"]


def test_duplicate_detection_distinguishes_identity_and_query() -> None:
    first = task("a")
    second = task("b")
    third = task("c", "  FIX   THE ledger ")
    assert exact_duplicate_groups([first, second, third]) == [["a", "b"]]
    assert query_duplicate_groups([first, second, third]) == [["a", "b", "c"]]


def test_recipe_driven_mutant_generation(tmp_path: Path) -> None:
    root = tmp_path / "task"
    root.mkdir()
    (root / "module.py").write_text("return value + 1\n")
    output = tmp_path / "mutants"
    artifacts = generate_mutants(root, [MutationRule("off-by-one", "module.py", "+ 1", "- 1")], output)
    assert len(artifacts) == 1
    assert (output / artifacts[0].output_path).read_text() == "return value - 1\n"
    assert json.loads((output / "manifest.json").read_text())["mutants"][0]["rule"] == "off-by-one"


def test_calibration_uses_full_pass_and_partial_reward() -> None:
    base = task()
    trajectories = [
        TrajectoryRecord(f"t{i}", base.task_id, base.task_version, base.task_hash, "model-a", "agent", i, f"hf://t{i}")
        for i in range(4)
    ]
    rewards = [
        RewardRecord(item.trajectory_id, base.task_id, base.task_version, base.task_hash, reward, "accept" if reward == 1 else "partial", "online")
        for item, reward in zip(trajectories, [1.0, 0.8, 0.5, 0.2])
    ]
    report = calibrate(rewards, {item.trajectory_id: item.model for item in trajectories})[0]
    assert report.full_pass_rate == 0.25
    assert report.label == "medium"
    assert report.mean_reward == pytest.approx(0.625)


def test_strict_delayed_reward_recovery(tmp_path: Path) -> None:
    trial = tmp_path / "trial"
    verifier = trial / "verifier"
    verifier.mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps({"id": "trajectory-1", "exception_info": {"exception_type": "RewardFileNotFoundError"}}))
    (verifier / "reward.txt").write_text("1.000000\n")
    (verifier / "reward.json").write_text(json.dumps({"reward": 1.0, "compliance": True, "anti_hack": True}))
    recovered = recover_trial(trial, task_id="task-1", task_version="1.0", task_hash="sha256:x")
    assert recovered is not None
    assert recovered.status == "accept_recovered"
    assert recovered.reward_source == "posthoc_artifact"


def test_recovery_rejects_mismatch_and_nonrecoverable_error(tmp_path: Path) -> None:
    trial = tmp_path / "trial"
    verifier = trial / "verifier"
    verifier.mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps({"exception_info": {"exception_type": "RuntimeError"}}))
    (verifier / "reward.txt").write_text("1\n")
    (verifier / "reward.json").write_text(json.dumps({"reward": 1.0}))
    assert recover_trial(trial, task_id="x", task_version="1", task_hash="h") is None


def test_hf_export_writes_deterministic_shards(tmp_path: Path) -> None:
    manifest = export_jsonl_shards(({"id": i} for i in range(5)), tmp_path, prefix="tasks", shard_size=2)
    assert manifest["records"] == 5
    assert len(manifest["files"]) == 3
    rows = []
    for name in manifest["files"]:
        rows.extend(json.loads(line) for line in (tmp_path / name).read_text().splitlines())
        assert manifest["checksums"][name].startswith("sha256:")
    assert rows == [{"id": i} for i in range(5)]


def test_formal_schemas_cover_serialized_record_fields() -> None:
    root = Path(__file__).parents[1] / "schemas"
    examples = {
        "task-record.schema.json": task().as_dict(),
        "trajectory-record.schema.json": TrajectoryRecord(
            "trajectory-1", task().task_id, task().task_version, task().task_hash,
            "model", "agent", 0, "hf://trajectory-1",
        ).as_dict(),
        "reward-record.schema.json": RewardRecord(
            "trajectory-1", task().task_id, task().task_version, task().task_hash,
            1.0, "accept", "online",
        ).as_dict(),
    }
    for name, example in examples.items():
        schema = json.loads((root / name).read_text())
        assert set(schema["required"]) <= set(example)
        assert set(example) <= set(schema["properties"])
