from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_package_fragment import compile_package_fragment  # noqa: E402
from materialize_model_bundle import materialize_bundle, validate_bundle  # noqa: E402
from merge_model_fragments import merge_fragments  # noqa: E402
from terminal_data_factory.multistep import validate_multistep_task  # noqa: E402


def inputs() -> tuple[dict, dict, dict, dict]:
    steps = []
    contract_steps = []
    names = []
    for position in range(1, 6):
        name = f"{position}-domain-stage-{position}"
        names.append(name)
        stage_id = f"stage-{position}"
        instruction = (
            f"Implement stage {position} with deterministic persistent behavior, "
            "explicit validation, canonical ordering, atomic failure semantics, "
            "and cumulative regression of all previously published APIs."
        )
        steps.append(
            {
                "id": stage_id,
                "title": f"Domain Stage {position}",
                "instruction": instruction,
                "public_api": [f"Engine.stage_{position}(self) -> int"],
                "public_cases": [f"stage_{position}_normal", f"stage_{position}_edge"],
                "hidden_categories": [
                    "atomic late failure",
                    "canonical ordering",
                    "read-only validation",
                ],
                "mutant": {
                    "name": f"breaks_stage_{position}",
                    "deterministic_fault": "Returns the wrong fixed result.",
                },
            }
        )
        contract_steps.append(
            {
                "position": position,
                "step_id": stage_id,
                "instruction": instruction,
                "public_api": [f"Engine.stage_{position}(self) -> int"],
                "public_cases": [f"stage_{position}_normal", f"stage_{position}_edge"],
            }
        )
    blueprint = {
        "schema_version": "1.0",
        "task_id": "mini-domain-engine",
        "title": "Deterministic Domain Engine",
        "domain": "test-domain",
        "trajectory_shape": "five-step-progressive-greenfield",
        "source": {
            "uri": "https://example.org/open-spec",
            "license": "Apache-2.0",
            "provenance": {
                "kind": "open-source-concept-study",
                "copied_code": False,
            },
        },
        "steps": steps,
    }
    contract = {
        "task_id": blueprint["task_id"],
        "contract_version": "1.0",
        "steps": contract_steps,
    }
    core_files = [
        {
            "path": "environment/codebase/domainengine/__init__.py",
            "executable": False,
            "content": "class Engine:\n    pass",
        }
    ]
    verification_files = [
        {
            "path": "environment/codebase/public_contract_tests/README.md",
            "executable": False,
            "content": "Run each public smoke against the cumulative implementation.",
        },
        {
            "path": "verifier/run_audit.py",
            "executable": True,
            "content": "#!/usr/bin/env python3\nraise SystemExit(0)",
        },
    ]
    cases = [
        {"name": f"case_{index}", "critical": True, "code": "assert True"}
        for index in range(7)
    ]
    for position, name in enumerate(names, 1):
        core_files.extend(
            [
                {
                    "path": f"steps/{name}/solution/files/impl.py",
                    "executable": False,
                    "content": f"VALUE = {position}",
                },
                {
                    "path": f"steps/{name}/solution/solve.sh",
                    "executable": True,
                    "content": "#!/bin/sh\ncp \"$(dirname \"$0\")/files/impl.py\" \"${TDF_WORKSPACE}/impl.py\"",
                },
            ]
        )
        verification_files.extend(
            [
                {
                    "path": f"environment/codebase/public_contract_tests/step_{position:02d}_smoke.py",
                    "executable": False,
                    "content": "assert True",
                },
                {
                    "path": f"steps/{name}/instruction.md",
                    "executable": False,
                    "content": (
                        "Read /app/knowledge/public_api.md and implement the "
                        f"contract. Run python public_contract_tests/step_{position:02d}_smoke.py."
                    ),
                },
                {
                    "path": f"steps/{name}/tests/test.sh",
                    "executable": True,
                    "content": (
                        "#!/bin/sh\n"
                        "env -u PYTHONPATH -u PYTHONHOME python -I verifier.py"
                    ),
                },
                {
                    "path": f"steps/{name}/tests/verifier.py",
                    "executable": False,
                    "content": (
                        f"CASES = {cases!r}\n"
                        'FLAGS = ["-I", "release_pass"]\n'
                        "correctness = 1.0\n"
                        'reward = {"release_pass": int(correctness == 1.0)}\n'
                    ),
                },
                {
                    "path": f"verifier/anti_cheat/fp{position}_step{position}_fault.py",
                    "executable": True,
                    "content": f"FAULT_STEP = {position}",
                },
            ]
        )
    core = {
        "schema_version": "1.0",
        "task_id": blueprint["task_id"],
        "fragment": "core",
        "files": core_files,
    }
    verification = {
        "schema_version": "1.0",
        "task_id": blueprint["task_id"],
        "fragment": "verification",
        "files": verification_files,
    }
    return blueprint, contract, core, verification


def test_compiled_package_is_static_validator_compatible(tmp_path: Path) -> None:
    blueprint, contract, core, verification = inputs()
    package = compile_package_fragment(blueprint, contract, core, verification)

    assert package["fragment"] == "package"
    by_path = {item["path"]: item for item in package["files"]}
    metadata = json.loads(by_path["metadata.json"]["content"])
    assert metadata["quality"]["behavioral_checks"] == 35
    assert metadata["quality"]["target_agent_rollouts"] == 0
    assert metadata["release_status"] == "under-construction"
    assert 'schema_version = "1.3"' in by_path["task.toml"]["content"]
    assert "Apache-2.0" in by_path["review/provenance_notes.md"]["content"]

    fragment_paths = []
    for name, fragment in (
        ("core", core),
        ("verification", verification),
        ("package", package),
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(fragment), encoding="utf-8")
        fragment_paths.append(path)
    merged = merge_fragments(fragment_paths)
    validated = validate_bundle(merged)
    task = tmp_path / "mini-domain-engine"
    materialize_bundle(validated, task)
    report = validate_multistep_task(task, require_evidence=False)
    assert report.errors == []


def test_compiler_rejects_unstatically_countable_cases() -> None:
    blueprint, contract, core, verification = inputs()
    verifier = next(
        item
        for item in verification["files"]
        if item["path"] == "steps/1-domain-stage-1/tests/verifier.py"
    )
    verifier["content"] = "CASES = make_cases()\n"
    with pytest.raises(ValueError, match="CASES must be a literal list"):
        compile_package_fragment(blueprint, contract, core, verification)


def test_compiler_counts_direct_literal_run_case_appends() -> None:
    blueprint, contract, core, verification = inputs()
    for item in verification["files"]:
        if item["path"].endswith("/tests/verifier.py"):
            item["content"] = "\n".join(
                [
                    "checks = []",
                    *[
                        f"checks.append(run_case('case_{index}', 'assert True', workspace))"
                        for index in range(7)
                    ],
                ]
            )
    package = compile_package_fragment(blueprint, contract, core, verification)
    metadata_item = next(
        item for item in package["files"] if item["path"] == "metadata.json"
    )
    assert json.loads(metadata_item["content"])["quality"]["behavioral_checks"] == 35


def test_compiler_counts_local_tuple_checks() -> None:
    blueprint, contract, core, verification = inputs()
    for item in verification["files"]:
        if item["path"].endswith("/tests/verifier.py"):
            item["content"] = "CHECKS = [\n" + ",\n".join(
                f"('case_{index}', lambda: {index})" for index in range(7)
            ) + "\n]\n"
    package = compile_package_fragment(blueprint, contract, core, verification)
    metadata_item = next(
        item for item in package["files"] if item["path"] == "metadata.json"
    )
    assert json.loads(metadata_item["content"])["quality"]["behavioral_checks"] == 35


def test_compiler_counts_shared_check_registry() -> None:
    blueprint, contract, core, verification = inputs()
    registry = ["CHECKS = {"]
    for position in range(1, 6):
        registry.append(
            f"'step-{position}': ["
            + ", ".join(f"('case_{index}', check_{index})" for index in range(7))
            + "],"
        )
    registry.append("}")
    verification["files"].append(
        {
            "path": "verifier/checks.py",
            "executable": False,
            "content": "\n".join(registry),
        }
    )
    for position, item in enumerate(
        [
            item
            for item in verification["files"]
            if item["path"].endswith("/tests/verifier.py")
        ],
        1,
    ):
        item["content"] = (
            "from verifier.checks import CHECKS\n"
            f"run_step('step-{position}', CHECKS['step-{position}'])\n"
        )
    package = compile_package_fragment(blueprint, contract, core, verification)
    metadata_item = next(
        item for item in package["files"] if item["path"] == "metadata.json"
    )
    assert json.loads(metadata_item["content"])["quality"]["behavioral_checks"] == 35


def test_compiler_counts_literal_get_checks_wrapper() -> None:
    blueprint, contract, core, verification = inputs()
    registry = ["_STEP_CHECKS = {"]
    for position in range(1, 6):
        registry.append(
            f"'step-{position}': ["
            + ", ".join(f"('case_{index}', check_{index})" for index in range(7))
            + "],"
        )
    registry.append("}")
    verification["files"].append(
        {
            "path": "verifier/step_checks.py",
            "executable": False,
            "content": "\n".join(registry),
        }
    )
    for position, item in enumerate(
        [
            item
            for item in verification["files"]
            if item["path"].endswith("/tests/verifier.py")
        ],
        1,
    ):
        item["content"] = (
            "from verifier.step_checks import get_checks\n"
            f"run_step('step-{position}', get_checks('step-{position}'))\n"
        )
    package = compile_package_fragment(blueprint, contract, core, verification)
    metadata_item = next(
        item for item in package["files"] if item["path"] == "metadata.json"
    )
    assert json.loads(metadata_item["content"])["quality"]["behavioral_checks"] == 35


def test_compiler_counts_static_step_checks_function() -> None:
    blueprint, contract, core, verification = inputs()
    lines = ["def step_checks(step):", "    C = Check"]
    for position in range(1, 6):
        cases = ", ".join(
            f"C('case_{index}', 'assert True')" for index in range(7)
        )
        lines.extend([f"    if step == {position}:", f"        return [{cases}]"])
    verification["files"].append(
        {
            "path": "verifier/common.py",
            "executable": False,
            "content": "\n".join(lines),
        }
    )
    for position, item in enumerate(
        [
            item
            for item in verification["files"]
            if item["path"].endswith("/tests/verifier.py")
        ],
        1,
    ):
        item["content"] = (
            "from verifier.common import run_verification\n"
            f"raise SystemExit(run_verification({position}))\n"
        )
    package = compile_package_fragment(blueprint, contract, core, verification)
    metadata_item = next(
        item for item in package["files"] if item["path"] == "metadata.json"
    )
    assert json.loads(metadata_item["content"])["quality"]["behavioral_checks"] == 35


def test_compiler_counts_static_step_case_factories() -> None:
    blueprint, contract, core, verification = inputs()
    lines = []
    for position in range(1, 6):
        cases = ", ".join(
            f"('case_{index}', 'assert True')" for index in range(7)
        )
        lines.extend(
            [f"def step{position}_cases():", f"    return [{cases}]", ""]
        )
    verification["files"].append(
        {
            "path": "verifier/cases.py",
            "executable": False,
            "content": "\n".join(lines),
        }
    )
    for position, item in enumerate(
        [
            item
            for item in verification["files"]
            if item["path"].endswith("/tests/verifier.py")
        ],
        1,
    ):
        item["content"] = (
            f"from verifier.cases import step{position}_cases\n"
            f"run_cases('step-{position}', step{position}_cases())\n"
        )
    package = compile_package_fragment(blueprint, contract, core, verification)
    metadata_item = next(
        item for item in package["files"] if item["path"] == "metadata.json"
    )
    assert json.loads(metadata_item["content"])["quality"]["behavioral_checks"] == 35


def test_compiler_rejects_fragment_task_mismatch() -> None:
    blueprint, contract, core, verification = inputs()
    verification["task_id"] = "mini-other-engine"
    with pytest.raises(ValueError, match="task_id differs"):
        compile_package_fragment(blueprint, contract, core, verification)
