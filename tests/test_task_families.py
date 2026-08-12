from __future__ import annotations

import json
from pathlib import Path

from terminal_data_factory.families import builtin_families
from terminal_data_factory.families.nl2repo import NL2RepoFamily
from terminal_data_factory.families.swe_bench import SWEBenchFamily
from terminal_data_factory.families.terminal_bench import TerminalBenchFamily


def test_registry_declares_five_benchmark_families() -> None:
    families = builtin_families()
    assert set(families) == {"terminal-bench", "swe-bench", "nl2repo", "deep-swe", "frontier-swe"}
    assert families["terminal-bench"].descriptor.harbor_native is True
    assert families["frontier-swe"].descriptor.expert_requirement == "high"


def test_terminal_bench_import_and_harbor_package(tmp_path: Path) -> None:
    source = tmp_path / "source" / "task-a"
    (source / "tests").mkdir(parents=True)
    (source / "instruction.md").write_text("Create /app/workspace/result.txt\n")
    (source / "tests/test.sh").write_text("#!/bin/sh\ntest -f /app/workspace/result.txt\n")
    (source / "task.toml").write_text(
        'schema_version = "1.3"\n'
        '[task]\nname = "demo/task-a"\n'
        '[metadata]\nhorizon = "short"\nreward_type = "binary"\n'
        '[environment]\nnetwork_mode = "no-network"\n'
        '[verifier]\ntimeout_sec = 30\n'
    )
    family = TerminalBenchFamily()
    records = family.import_records(tmp_path / "source", source_ref="hf://demo/terminal", dataset_version="1.0")
    assert len(records) == 1
    assert records[0].workspace_kind == "filesystem"
    assert family.validate_record(records[0]) == []
    packaged = family.package_for_harbor(
        tmp_path / "source", tmp_path / "harbor", source_ref="hf://demo/terminal", dataset_version="1.0",
    )
    assert (packaged[0] / "task.toml").is_file()
    sidecar = json.loads((packaged[0] / "swefoundry-task-record.json").read_text())
    assert sidecar["task_hash"] == records[0].task_hash


def test_swe_bench_import_preserves_repo_and_tests(tmp_path: Path) -> None:
    source = tmp_path / "swe.jsonl"
    source.write_text(json.dumps({
        "instance_id": "project__repo-1",
        "repo": "project/repo",
        "base_commit": "abc123",
        "problem_statement": "Fix the parser.",
        "FAIL_TO_PASS": '["tests/test_parser.py::test_bug"]',
        "PASS_TO_PASS": '["tests/test_parser.py::test_existing"]',
    }) + "\n")
    family = SWEBenchFamily()
    record = family.import_records(source, source_ref="hf://swe-bench/test", dataset_version="verified-1")[0]
    assert record.workspace["repo_url"] == "https://github.com/project/repo"
    assert record.workspace["base_commit"] == "abc123"
    assert record.verifier["fail_to_pass"] == ["tests/test_parser.py::test_bug"]
    assert family.validate_record(record) == []


def test_nl2repo_import_requires_machine_checkable_contract(tmp_path: Path) -> None:
    source = tmp_path / "nl2repo.jsonl"
    rows = [
        {"task_id": "good", "instruction": "Build a URL router.", "language": "python", "contract": {"commands": ["pytest"]}},
        {"task_id": "weak", "instruction": "Build something.", "language": "python"},
    ]
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    family = NL2RepoFamily()
    good, weak = family.import_records(source, source_ref="hf://demo/nl2repo", dataset_version="1")
    assert good.workspace_kind == "empty_repo"
    assert family.validate_record(good) == []
    assert "behavioral contract" in family.validate_record(weak)[0]
