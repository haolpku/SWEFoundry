from __future__ import annotations

import json
from pathlib import Path

import pytest

from terminal_data_factory.repair import (
    apply_repairs_transactionally,
    build_task_snapshot,
    classify_task_failure,
    compare_qa_generation,
    promote_non_regressing_generation,
    validate_repair_payload,
)


def _task(root: Path, name: str = "mini-example") -> Path:
    task = root / name
    (task / "environment/codebase").mkdir(parents=True)
    (task / "steps/1-one/solution").mkdir(parents=True)
    (task / "verifier").mkdir()
    (task / "task.toml").write_text('schema_version = "1.3"\n')
    (task / "environment/codebase/value.py").write_text("VALUE = 1\n")
    (task / "steps/1-one/solution/solve.sh").write_text("#!/bin/sh\n")
    return task


def _result(task_id: str, *, steps: int, audit: bool, passed: bool) -> dict:
    return {
        "task_id": task_id,
        "passed": passed,
        "audit": {"passed": audit},
        "progressive_oracle": {
            "passed": steps == 5,
            "steps_passed": steps,
            "steps": [],
        },
        "independent_inventory": {"passed": True},
        "static_validation": {"passed": True},
        "scan": {"passed": True},
    }


def test_classifier_identifies_syntax_and_hidden_behavior() -> None:
    result = _result("mini-example", steps=4, audit=False, passed=False)
    result["progressive_oracle"]["steps"] = [
        {
            "position": 5,
            "step": "5-integrate",
            "passed": False,
            "installs": [{"returncode": 0}],
            "public_smoke": {"returncode": 0, "stderr_tail": ""},
            "verifier": {
                "returncode": 1,
                "stderr_tail": "SyntaxError: unmatched ')'",
            },
            "metrics": {"release_pass": 0},
        }
    ]

    classified = classify_task_failure(result)

    assert "audit-gate" in classified["categories"]
    assert "hidden-behavior" in classified["categories"]
    assert "syntax-or-escaping" in classified["categories"]


def test_repair_payload_rejects_traversal_and_protected_files() -> None:
    base = {
        "schema_version": "1.0",
        "task_id": "mini-example",
        "diagnosis": "fix",
        "files": [
            {
                "path": "../escape.py",
                "content": "pass\n",
                "executable": False,
            }
        ],
    }
    with pytest.raises(ValueError, match="unsafe repair path"):
        validate_repair_payload(base, expected_task_id="mini-example")
    base["files"][0]["path"] = "verifier/audit-report.json"
    with pytest.raises(ValueError, match="protected file"):
        validate_repair_payload(base, expected_task_id="mini-example")


def test_snapshot_and_transactional_apply_preserve_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    task = _task(source)
    snapshot = build_task_snapshot(task)
    assert snapshot["task_id"] == "mini-example"
    repairs = {
        "mini-example": {
            "schema_version": "1.0",
            "task_id": "mini-example",
            "diagnosis": "correct value",
            "files": [
                {
                    "path": "environment/codebase/value.py",
                    "content": "VALUE = 2\n",
                    "executable": False,
                }
            ],
        }
    }

    result = apply_repairs_transactionally(
        source,
        repairs,
        tmp_path / "output",
    )

    assert result["source_unchanged"] is True
    assert (task / "environment/codebase/value.py").read_text() == "VALUE = 1\n"
    assert (
        tmp_path / "output/mini-example/environment/codebase/value.py"
    ).read_text() == "VALUE = 2\n"


def test_qa_comparison_reports_improvement_and_regression() -> None:
    before = {
        "tasks": [
            _result("a", steps=2, audit=False, passed=False),
            _result("b", steps=5, audit=True, passed=True),
        ]
    }
    after = {
        "tasks": [
            _result("a", steps=5, audit=True, passed=True),
            _result("b", steps=4, audit=False, passed=False),
        ]
    }

    comparison = compare_qa_generation(before, after)

    assert comparison["improved"] == 1
    assert comparison["regressed"] == 1
    assert comparison["passed"] is False


def test_promotion_uses_only_strictly_improved_tasks(tmp_path: Path) -> None:
    before_root = tmp_path / "before"
    after_root = tmp_path / "after"
    _task(before_root, "a")
    _task(before_root, "b")
    _task(after_root, "a")
    _task(after_root, "b")
    (after_root / "a/environment/codebase/value.py").write_text("VALUE = 2\n")
    (after_root / "b/environment/codebase/value.py").write_text("VALUE = 3\n")
    before = {
        "tasks": [
            _result("a", steps=2, audit=False, passed=False),
            _result("b", steps=5, audit=True, passed=True),
        ]
    }
    after = {
        "tasks": [
            _result("a", steps=5, audit=True, passed=True),
            _result("b", steps=4, audit=False, passed=False),
        ]
    }

    result = promote_non_regressing_generation(
        before_root,
        after_root,
        before,
        after,
        tmp_path / "promoted",
    )

    assert result["promoted"] == 1
    assert (
        tmp_path / "promoted/a/environment/codebase/value.py"
    ).read_text() == "VALUE = 2\n"
    assert (
        tmp_path / "promoted/b/environment/codebase/value.py"
    ).read_text() == "VALUE = 1\n"
