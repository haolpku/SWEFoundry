from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_family_smoke.py"
SPEC = importlib.util.spec_from_file_location("validate_family_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_family_smoke_batch_has_three_distinct_passing_tasks() -> None:
    tasks_root = ROOT / "examples/family-smoke-v1/tasks"
    reports = [
        MODULE.audit_task(task)
        for task in sorted(tasks_root.iterdir())
        if (task / "task.toml").is_file()
    ]
    assert len(reports) == 3
    assert {report["task_id"] for report in reports} == {
        "build-feature-flags",
        "repair-jsonl-ledger",
        "reproduce-url-router",
    }
    assert all(report["passed"] for report in reports), reports
    assert all(report["deterministic"] for report in reports)
    assert all(report["starter_reward"] < 1.0 for report in reports)
    assert all(report["oracle_rewards"] == [1.0, 1.0] for report in reports)
