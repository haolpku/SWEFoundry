from __future__ import annotations

import json
from pathlib import Path

import pytest

import terminal_data_factory.batch_qa as batch_qa
from terminal_data_factory.multistep import MultiStepReport


AUDIT_SCRIPT = """\
from __future__ import annotations
import json
from pathlib import Path

output = Path(__file__).with_name("audit-report.json")
output.write_text(json.dumps({"passed": True}, sort_keys=True) + "\\n")
raise SystemExit(0)
"""


def make_fake_task(root: Path, name: str = "mini-test") -> Path:
    task = root / name
    (task / "verifier").mkdir(parents=True)
    (task / "task.toml").write_text('schema_version = "1.3"\n')
    (task / "verifier/run_audit.py").write_text(AUDIT_SCRIPT)
    (task / "README.md").write_text("clean fixture\n")
    return task


def make_progressive_task(root: Path, broken_step: int | None = None) -> Path:
    task = root / "mini-progressive"
    codebase = task / "environment/codebase"
    (codebase / "public_contract_tests").mkdir(parents=True)
    (task / "verifier").mkdir(parents=True)
    step_names = [f"{number}-step-{number}" for number in range(1, 6)]
    step_config = "\n".join(
        f'[[steps]]\nname = "{step_name}"' for step_name in step_names
    )
    (task / "task.toml").write_text(
        f'schema_version = "1.3"\n{step_config}\n'
    )
    (codebase / "state.txt").write_text("0\n")
    for position, step_name in enumerate(step_names, 1):
        smoke = codebase / "public_contract_tests" / f"step_{position:02d}_smoke.py"
        smoke.write_text(
            "from pathlib import Path\n"
            f"assert Path(__file__).parents[1].joinpath('state.txt').read_text().strip() == '{position}'\n"
        )
        step = task / "steps" / step_name
        (step / "solution").mkdir(parents=True)
        (step / "tests").mkdir()
        written_value = position - 1 if broken_step == position else position
        solve = step / "solution/solve.sh"
        solve.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            f"printf '{written_value}\\n' > \"$TDF_WORKSPACE/environment/codebase/state.txt\"\n"
        )
        solve.chmod(0o755)
        verifier = step / "tests/verifier.py"
        verifier.write_text(
            "import json, os\n"
            "from pathlib import Path\n"
            "workspace = Path(os.environ['TDF_WORKSPACE'])\n"
            "reward = Path(os.environ['TDF_REWARD_DIR'])\n"
            f"passed = workspace.joinpath('environment/codebase/state.txt').read_text().strip() == '{position}'\n"
            "reward.mkdir(parents=True, exist_ok=True)\n"
            "reward.joinpath('reward.json').write_text(json.dumps({"
            "'release_pass': int(passed), 'correctness': float(passed)}))\n"
            "raise SystemExit(0 if passed else 1)\n"
        )
        test_sh = step / "tests/test.sh"
        test_sh.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "exec \"$TDF_PYTHON\" -I \"$(dirname \"$0\")/verifier.py\"\n"
        )
        test_sh.chmod(0o755)
    return task


def test_batch_qa_is_read_only_and_audit_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = make_fake_task(tmp_path / "batch")
    monkeypatch.setattr(
        batch_qa,
        "validate_multistep_task",
        lambda path, require_evidence: MultiStepReport(path.name),
    )
    monkeypatch.setattr(
        batch_qa,
        "_progressive_oracle_copy",
        lambda path, timeout: {
            "passed": True,
            "steps_passed": 5,
            "steps": [],
        },
    )
    monkeypatch.setattr(
        batch_qa,
        "_independent_inventory",
        lambda path: {
            "passed": True,
            "behavioral_checks": 35,
            "mutants": 5,
            "public_smokes": 5,
        },
    )

    summary = batch_qa.run_batch_qa(tmp_path / "batch", repeats=2, timeout=10)

    assert summary["passed"] is True
    assert summary["task_count"] == 1
    assert summary["tasks"][0]["audit"]["deterministic"] is True
    assert summary["tasks"][0]["progressive_oracle"]["passed"] is True
    assert summary["tasks"][0]["independent_inventory"]["passed"] is True
    assert summary["tasks"][0]["source_unchanged"] is True
    assert not (task / "verifier/audit-report.json").exists()


def test_progressive_oracle_executes_each_cumulative_solution(
    tmp_path: Path,
) -> None:
    task = make_progressive_task(tmp_path)

    result = batch_qa._progressive_oracle_copy(task, timeout=10)

    assert result["passed"] is True
    assert result["steps_passed"] == 5


def test_progressive_oracle_rejects_broken_intermediate_solution(
    tmp_path: Path,
) -> None:
    task = make_progressive_task(tmp_path, broken_step=3)

    result = batch_qa._progressive_oracle_copy(task, timeout=10)

    assert result["passed"] is False
    assert result["steps_passed"] == 4
    assert result["steps"][2]["passed"] is False
    assert result["steps"][2]["public_smoke"]["returncode"] != 0
    assert result["steps"][2]["metrics"]["release_pass"] == 0


def test_scan_reports_findings_without_echoing_secret(tmp_path: Path) -> None:
    task = make_fake_task(tmp_path)
    leaked = "sk-" + ("a" * 24)
    endpoint = "http://" + "192.0.2.1:3000/v1"
    user_path = "/Users/" + "example/work/data"
    (task / "leaks.txt").write_text(
        f"{leaked}\n{endpoint}\n{user_path}\n"
    )
    cache = task / "__pycache__"
    cache.mkdir()
    (cache / "module.pyc").write_bytes(b"bytecode")

    scan = batch_qa.scan_task(task)
    serialized = json.dumps(scan)

    assert scan["passed"] is False
    assert scan["counts"] == {
        "secrets": 1,
        "endpoints": 1,
        "absolute_paths": 1,
        "python_bytecode": 2,
    }
    assert leaked not in serialized


def test_discovery_refuses_more_than_ten_tasks(tmp_path: Path) -> None:
    for number in range(11):
        make_fake_task(tmp_path, f"task-{number:02d}")

    with pytest.raises(ValueError, match="limit is 10"):
        batch_qa.discover_batch_tasks(tmp_path)


def test_summary_cannot_be_written_inside_source(tmp_path: Path) -> None:
    root = tmp_path / "batch"
    root.mkdir()

    with pytest.raises(ValueError, match="outside the source"):
        batch_qa.write_summary({"passed": True}, root / "summary.json", root)
