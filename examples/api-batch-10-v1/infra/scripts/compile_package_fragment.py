#!/usr/bin/env python3
"""Compile deterministic Harbor/package files from accepted model artifacts."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from terminal_data_factory.operators.core import atomic_json

from merge_model_fragments import validate_task_id


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _unwrap_single(value: dict, singular: str, plural: str) -> dict:
    if isinstance(value.get("data"), dict):
        return _unwrap_single(value["data"], singular, plural)
    if singular in value and isinstance(value[singular], dict):
        return value[singular]
    if plural in value:
        items = value[plural]
        if not isinstance(items, list) or len(items) != 1:
            raise ValueError(f"{plural} input must contain exactly one item")
        if not isinstance(items[0], dict):
            raise ValueError(f"{plural} item must be an object")
        return items[0]
    return value


def _slug(value: object) -> str:
    rendered = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return rendered or "step"


def _step_names(blueprint: dict) -> list[str]:
    steps = blueprint.get("steps")
    if not isinstance(steps, list) or len(steps) != 5:
        raise ValueError("blueprint must contain exactly five steps")
    names: list[str] = []
    for position, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise ValueError(f"blueprint step {position} must be an object")
        step_id = _slug(step.get("id", ""))
        generic_ids = {f"stage-{position}", f"step-{position}", str(position)}
        if re.match(fr"^{position}-", step_id) and step_id not in generic_ids:
            name = step_id
        else:
            name = f"{position}-{_slug(step.get('title') or step_id)}"
        names.append(name)
    if len(set(names)) != 5:
        raise ValueError("derived step names are not unique")
    return names


def _fragment_files(fragment: dict, expected_name: str, task_id: str) -> dict[str, dict]:
    if fragment.get("schema_version") != "1.0":
        raise ValueError(f"{expected_name} fragment schema_version must be 1.0")
    if fragment.get("fragment") != expected_name:
        raise ValueError(f"expected fragment={expected_name!r}")
    if fragment.get("task_id") != task_id:
        raise ValueError(f"{expected_name} fragment task_id differs")
    files = fragment.get("files")
    if not isinstance(files, list):
        raise ValueError(f"{expected_name} fragment files must be a list")
    result: dict[str, dict] = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "executable",
            "content",
        }:
            raise ValueError(
                f"{expected_name}: every file must have path/executable/content"
            )
        path = PurePosixPath(str(item["path"]))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError(f"{expected_name}: unsafe path {path}")
        key = path.as_posix()
        if key in result:
            raise ValueError(f"{expected_name}: duplicate path {key}")
        if not isinstance(item["content"], str):
            raise ValueError(f"{expected_name}: non-string content {key}")
        result[key] = item
    return result


def _named_ast_sequence_count(node: ast.AST, path: str, variable: str) -> int:
    """Count literal names in a list/tuple of dicts or named tuples.

    The executable body may contain arbitrary Python expressions, but the case
    container and every case name must be statically visible.
    """

    if not isinstance(node, (ast.List, ast.Tuple)):
        raise ValueError(f"{path}: {variable} must be a literal list or tuple")
    names: list[str] = []
    for item in node.elts:
        name: object | None = None
        if isinstance(item, ast.Dict):
            for key, value in zip(item.keys, item.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "name"
                    and isinstance(value, ast.Constant)
                ):
                    name = value.value
                    break
            if not any(
                isinstance(key, ast.Constant) and key.value == "code"
                for key in item.keys
            ):
                raise ValueError(f"{path}: every {variable} dict needs literal name/code")
        elif (
            isinstance(item, (ast.Tuple, ast.List))
            and len(item.elts) >= 2
            and isinstance(item.elts[0], ast.Constant)
        ):
            name = item.elts[0].value
        elif (
            isinstance(item, ast.Call)
            and len(item.args) >= 2
            and isinstance(item.args[0], ast.Constant)
        ):
            # Dataclass/factory declarations such as
            # ``Check("canonical_order", code)`` remain statically named.
            name = item.args[0].value
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{path}: every {variable} item needs a literal name")
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError(f"{path}: duplicate {variable} names")
    return len(names)


def _shared_check_counts(files: dict[str, dict]) -> dict[str, int]:
    """Read strict shared literal case registries/functions from verifier files."""

    result: dict[str, int] = {}
    for path, item in files.items():
        if not path.startswith("verifier/") or not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(item["content"], filename=path)
        except SyntaxError as exc:
            raise ValueError(f"{path}: verifier is not valid Python: {exc}") from exc
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not re.fullmatch(r"step[1-5]_cases", node.name):
                    continue
                returns = [
                    child
                    for child in node.body
                    if isinstance(child, ast.Return) and child.value is not None
                ]
                if len(returns) != 1 or len(node.body) != 1:
                    raise ValueError(
                        f"{path}: {node.name} must contain one literal return"
                    )
                if node.name in result:
                    raise ValueError(f"{path}: duplicate shared case function {node.name}")
                result[node.name] = _named_ast_sequence_count(
                    returns[0].value, path, node.name
                )
                continue
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            registry_name = next(
                (
                    target.id
                    for target in targets
                    if isinstance(target, ast.Name)
                    and target.id in {"CHECKS", "_STEP_CHECKS"}
                ),
                None,
            )
            if registry_name is None:
                continue
            if not isinstance(node.value, ast.Dict):
                # A local list-style CHECKS declaration is handled by _case_count.
                continue
            for key, value in zip(node.value.keys, node.value.values):
                if (
                    not isinstance(key, ast.Constant)
                    or not isinstance(key.value, str)
                    or not key.value.strip()
                ):
                    raise ValueError(
                        f"{path}: {registry_name} registry keys must be literal strings"
                    )
                if key.value in result:
                    raise ValueError(f"{path}: duplicate shared CHECKS key {key.value}")
                result[key.value] = _named_ast_sequence_count(
                    value, path, f"{registry_name}[{key.value!r}]"
                )
        for function in (
            node for node in tree.body if isinstance(node, ast.FunctionDef)
        ):
            factory_match = re.fullmatch(r"step([1-5])_cases", function.name)
            if factory_match:
                returns = [
                    statement
                    for statement in function.body
                    if isinstance(statement, ast.Return)
                ]
                if len(function.body) != 1 or len(returns) != 1 or returns[0].value is None:
                    raise ValueError(
                        f"{path}: {function.name} must contain one literal return"
                    )
                key = f"__factory_{function.name}"
                if key in result:
                    raise ValueError(f"{path}: duplicate case factory {function.name}")
                result[key] = _named_ast_sequence_count(
                    returns[0].value, path, function.name
                )
                continue
            if function.name != "step_checks" or not function.args.args:
                continue
            parameter = function.args.args[0].arg
            for branch in function.body:
                if not isinstance(branch, ast.If):
                    continue
                test = branch.test
                if (
                    not isinstance(test, ast.Compare)
                    or not isinstance(test.left, ast.Name)
                    or test.left.id != parameter
                    or len(test.ops) != 1
                    or not isinstance(test.ops[0], ast.Eq)
                    or len(test.comparators) != 1
                    or not isinstance(test.comparators[0], ast.Constant)
                    or not isinstance(test.comparators[0].value, int)
                ):
                    continue
                returns = [
                    statement
                    for statement in branch.body
                    if isinstance(statement, ast.Return)
                ]
                if len(returns) != 1 or returns[0].value is None:
                    raise ValueError(
                        f"{path}: step_checks branch needs one literal return"
                    )
                key = f"__position_{test.comparators[0].value}"
                if key in result:
                    raise ValueError(f"{path}: duplicate step_checks branch {key}")
                result[key] = _named_ast_sequence_count(
                    returns[0].value, path, f"step_checks({test.comparators[0].value})"
                )
    return result


def _referenced_shared_check_key(source: str, path: str) -> str | None:
    tree = ast.parse(source, filename=path)
    keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "CHECKS"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_cases"
        ):
            for argument in node.args:
                if (
                    isinstance(argument, ast.Call)
                    and isinstance(argument.func, ast.Name)
                    and re.fullmatch(r"step[1-5]_cases", argument.func.id)
                ):
                    keys.add(argument.func.id)
    if len(keys) > 1:
        raise ValueError(f"{path}: wrapper references multiple shared CHECKS keys")
    if keys:
        return next(iter(keys))
    getter_keys: set[str] = set()
    runner_keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if (
            node.func.id == "get_checks"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            getter_keys.add(node.args[0].value)
        if (
            node.func.id in {"run_step", "run_cases"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            runner_keys.add(node.args[0].value)
    if len(getter_keys) > 1:
        raise ValueError(f"{path}: wrapper calls get_checks with multiple keys")
    if getter_keys:
        key = next(iter(getter_keys))
        if runner_keys and runner_keys != {key}:
            raise ValueError(f"{path}: get_checks key differs from Step runner key")
        return key
    positions: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_verification"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, int)
        ):
            positions.add(node.args[0].value)
    if len(positions) > 1:
        raise ValueError(f"{path}: wrapper references multiple Step positions")
    if positions:
        return f"__position_{next(iter(positions))}"
    factories: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and re.fullmatch(r"step[1-5]_cases", node.func.id)
        ):
            factories.add(node.func.id)
    if len(factories) > 1:
        raise ValueError(f"{path}: wrapper references multiple Step case factories")
    return f"__factory_{next(iter(factories))}" if factories else None


def _case_count(source: str, path: str, shared_counts: dict[str, int]) -> int:
    """Count only literal named cases in supported verifier declarations."""

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise ValueError(f"{path}: verifier is not valid Python: {exc}") from exc
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        variable = next(
            (
                target.id
                for target in targets
                if isinstance(target, ast.Name) and target.id in {"CASES", "CHECKS"}
            ),
            None,
        )
        if variable is None:
            continue
        value_node = node.value
        if value_node is None:
            raise ValueError(f"{path}: {variable} has no value")
        if variable == "CHECKS" and isinstance(value_node, ast.Dict):
            # Shared registries are counted at their declaration, not as a
            # step-local case set.
            continue
        return _named_ast_sequence_count(value_node, path, variable)

    # Some verifier workers construct a result list with one explicit
    # ``checks.append(run_case("name", ...))`` statement per behavior. Count
    # only direct literal calls; loops, comprehensions and computed names are
    # deliberately excluded.
    names = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        append = node.value
        if (
            not isinstance(append.func, ast.Attribute)
            or append.func.attr != "append"
            or not isinstance(append.func.value, ast.Name)
            or append.func.value.id != "checks"
            or len(append.args) != 1
            or not isinstance(append.args[0], ast.Call)
        ):
            continue
        run_case = append.args[0]
        if (
            not isinstance(run_case.func, ast.Name)
            or run_case.func.id != "run_case"
            or not run_case.args
            or not isinstance(run_case.args[0], ast.Constant)
            or not isinstance(run_case.args[0].value, str)
            or not run_case.args[0].value.strip()
        ):
            continue
        names.append(run_case.args[0].value)
    if names:
        if len(set(names)) != len(names):
            raise ValueError(f"{path}: duplicate run_case names")
        return len(names)
    shared_key = _referenced_shared_check_key(source, path)
    if shared_key is not None:
        if shared_key not in shared_counts:
            raise ValueError(f"{path}: unknown shared CHECKS key {shared_key!r}")
        return shared_counts[shared_key]
    raise ValueError(f"{path}: no statically countable named behavior cases found")


def _toml_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _file(path: str, content: str, executable: bool = False) -> dict:
    return {"path": path, "executable": executable, "content": content.rstrip() + "\n"}


def compile_package_fragment(
    blueprint_input: dict,
    contract_input: dict,
    core_fragment: dict,
    verification_fragment: dict,
) -> dict:
    blueprint = _unwrap_single(blueprint_input, "blueprint", "blueprints")
    contract = _unwrap_single(contract_input, "contract", "contracts")
    task_id = validate_task_id(blueprint.get("task_id"))
    if contract.get("task_id") != task_id:
        raise ValueError("contract task_id differs from blueprint")
    step_names = _step_names(blueprint)
    blueprint_steps = blueprint["steps"]
    contract_steps = contract.get("steps")
    if not isinstance(contract_steps, list) or len(contract_steps) != 5:
        raise ValueError("contract must contain exactly five steps")
    for position, (blueprint_step, contract_step) in enumerate(
        zip(blueprint_steps, contract_steps), 1
    ):
        if not isinstance(contract_step, dict):
            raise ValueError(f"contract step {position} must be an object")
        contract_position = contract_step.get("position", contract_step.get("number"))
        if contract_position != position:
            raise ValueError("contract positions must be exactly 1 through 5")
        contract_id = contract_step.get("step_id", contract_step.get("id"))
        if contract_id is not None and str(contract_id) != str(blueprint_step.get("id")):
            raise ValueError(f"contract step {position} id differs from blueprint")
        if len(contract_step.get("public_cases", [])) < 2:
            raise ValueError(f"contract step {position} needs two public cases")

    core_files = _fragment_files(core_fragment, "core", task_id)
    verification_files = _fragment_files(
        verification_fragment, "verification", task_id
    )
    overlap = set(core_files) & set(verification_files)
    if overlap:
        raise ValueError(f"core/verification paths overlap: {sorted(overlap)}")

    for name in step_names:
        core_prefix = f"steps/{name}/solution/"
        if not any(path.startswith(core_prefix) for path in core_files):
            raise ValueError(f"core fragment has no solution for {name}")
        verifier_path = f"steps/{name}/tests/verifier.py"
        if verifier_path not in verification_files:
            raise ValueError(f"verification fragment missing {verifier_path}")

    shared_counts = _shared_check_counts(verification_files)
    counts = {
        name: _case_count(
            verification_files[f"steps/{name}/tests/verifier.py"]["content"],
            f"steps/{name}/tests/verifier.py",
            shared_counts,
        )
        for name in step_names
    }
    behavioral_checks = sum(counts.values())
    if behavioral_checks < 30:
        raise ValueError(
            f"only {behavioral_checks} statically confirmed behavioral checks; need 30"
        )

    package_names = sorted(
        {
            PurePosixPath(path).parts[2]
            for path in core_files
            if len(PurePosixPath(path).parts) >= 4
            and PurePosixPath(path).parts[:2] == ("environment", "codebase")
            and PurePosixPath(path).parts[2] != "public_contract_tests"
        }
    )
    if len(package_names) != 1:
        raise ValueError(
            f"expected one starter package under environment/codebase, got {package_names}"
        )
    package_name = package_names[0]

    source = blueprint.get("source") or {}
    source_uri = str(source.get("uri") or blueprint.get("source_uri") or "").strip()
    source_license = str(
        source.get("license") or blueprint.get("license") or ""
    ).strip()
    provenance = source.get("provenance") or blueprint.get("provenance") or {}
    if not source_uri or not source_license:
        raise ValueError("blueprint source URI and license are required")
    if provenance.get("copied_code") is not False:
        raise ValueError("provenance must explicitly declare copied_code=false")

    title = str(blueprint.get("title") or task_id)
    domain = str(blueprint.get("domain") or "engineering-systems")
    trajectory = str(
        blueprint.get("trajectory_shape") or "five-step-progressive-greenfield"
    )
    description = (
        f"Build {title} as an offline, deterministic Python system in five "
        "progressive implementation steps."
    )
    public_steps = []
    for position, (name, step) in enumerate(zip(step_names, contract_steps), 1):
        public_steps.append(
            {
                "number": position,
                "name": name,
                "public_api": list(step.get("public_api", [])),
                "public_cases": list(step.get("public_cases", [])),
            }
        )
    public_api = {
        "schema_version": "1.0",
        "package": package_name,
        "steps": public_steps,
        "policy": {
            "hidden_tests_must_not_require_undisclosed_public_names": True,
            "final_step_regresses_steps_1_through_4": True,
        },
    }

    task_lines = [
        'schema_version = "1.3"',
        'multi_step_reward_strategy = "final"',
        'artifacts = ["/app/workspace"]',
        "",
        "[task]",
        f"name = {_toml_string(f'terminal-data-factory/{task_id}')}",
        f"description = {_toml_string(description)}",
        'authors = [{ name = "Terminal Data Factory Team" }]',
        f"keywords = [{_toml_string(domain)}, \"greenfield\", \"multi-step\"]",
        "",
    ]
    for name in step_names:
        task_lines.extend(
            [
                "[[steps]]",
                f"name = {_toml_string(name)}",
                "[steps.verifier]",
                "timeout_sec = 300.0",
                "[steps.agent]",
                "timeout_sec = 7200.0",
                "",
            ]
        )
    task_lines.extend(
        [
            "[metadata]",
            'difficulty = "uncalibrated-long-horizon-candidate"',
            'calibration_status = "target-agent-rollouts-required"',
            'language = "python"',
            f"domain = {_toml_string(domain)}",
            'codebase_profile = "greenfield"',
            f"trajectory_shape = {_toml_string(trajectory)}",
            "",
            "[verifier]",
            "timeout_sec = 300.0",
            "",
            "[agent]",
            "timeout_sec = 40000.0",
            "max_steps = 500",
            "",
            "[environment]",
            "build_timeout_sec = 300.0",
            'os = "linux"',
            "cpus = 2",
            "memory_mb = 4096",
            "storage_mb = 8192",
            "gpus = 0",
            "allow_internet = false",
            'workdir = "/app/workspace"',
        ]
    )
    metadata = {
        "schema_version": "1.0",
        "task_id": task_id,
        "product_type": "multi-step-greenfield",
        "steps": 5,
        "release_status": "under-construction",
        "difficulty": {
            "label": "uncalibrated-long-horizon-candidate",
            "evidence_required": "repeated cross-family target-agent rollouts",
        },
        "quality": {
            "behavioral_checks": behavioral_checks,
            "behavioral_checks_by_step": counts,
            "curated_false_positives": 5,
            "target_agent_rollouts": 0,
        },
        "provenance": {
            "kind": str(provenance.get("kind") or "open-source-concept-study"),
            "source": source_uri,
            "source_license": source_license,
            "copied_code": False,
            "contains_proprietary_data": False,
            "owner": "Terminal Data Factory Team",
        },
        "license": {
            "status": "pending-owner-approval",
            "distribution": "expert-review-only",
        },
    }

    public_md_parts = [
        "# Public API contract",
        "",
        f"Package: `{package_name}`",
        "",
        "Hidden tests may exercise only names and observable behavior disclosed here.",
    ]
    for step in public_steps:
        public_md_parts.extend(
            [
                "",
                f"## Step {step['number']}: {step['name']}",
                "",
                "Public API:",
                *[f"- `{item}`" for item in step["public_api"]],
                "",
                "Public behavior cases:",
                *[f"- `{item}`" for item in step["public_cases"]],
            ]
        )
    architecture_parts = [
        "# Architecture and semantic boundaries",
        "",
        description,
        "",
        "The candidate is an offline concept study. State, ordering, validation, "
        "and recovery behavior must be deterministic and observable through the "
        "published API. Candidate implementations must not depend on network "
        "availability, process-salted hashing, wall-clock time, locale, UUIDs, "
        "or host directory ordering.",
        "",
    ]
    for position, (name, step) in enumerate(zip(step_names, blueprint_steps), 1):
        architecture_parts.extend(
            [
                f"## Step {position}: {name}",
                "",
                str(step.get("instruction") or "").strip(),
                "",
                "Verifier semantic categories:",
                *[
                    f"- {item}"
                    for item in step.get("hidden_categories", [])
                ],
                "",
                "The Step solution is applied cumulatively. Previously published "
                "behavior remains part of the final system contract.",
                "",
            ]
        )
    index_md = f"""# Knowledge index

This local corpus defines the public surface and engineering boundaries for
`{task_id}`. It is agent-visible at `/app/knowledge` and is the authoritative
contract for the offline benchmark.

Documents:

- `public_api.md`: exact public signatures and named public behavior cases.
- `public_api.json`: machine-readable Step 1–5 contract.
- `architecture.md`: subsystem progression, semantic boundaries, and integration rules.

Provenance:

The task is a concept study informed by {source_uri}, licensed as
{source_license}. No upstream implementation code or proprietary data was
copied. The citation supplies domain framing only; the benchmark implementation
and tests are newly authored and remain under expert review.
"""
    readme = f"""# {title}

`{task_id}` is a five-step, offline Greenfield terminal benchmark candidate in
the `{domain}` domain.

The five cumulative Steps are:

{chr(10).join(f"{index}. `{name}`" for index, name in enumerate(step_names, 1))}

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
{behavioral_checks} statically countable checks across the five Steps.

Status: `under-construction`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of {source_uri} ({source_license}); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
"""
    dockerfile = f"""FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/workspace
COPY codebase/ /app/workspace/
COPY knowledge/ /app/knowledge/
RUN python -m compileall -q /app/workspace
CMD ["/bin/sh"]
"""
    provenance_notes = f"""# Provenance notes

- Source: {source_uri}
- Source license: {source_license}
- Provenance kind: {metadata['provenance']['kind']}
- Copied upstream code: no
- Contains proprietary data: no

The source is used only for domain concepts. Generated core, verification,
knowledge, rubric and packaging files are newly authored. An expert must
confirm that the bounded semantics are accurate and that distribution is
compatible with the cited source before release.

Current distribution is expert-review-only and release status is
under-construction.
"""
    verifier_notes = f"""# Verifier compilation notes

The package compiler statically parsed literal `CASES` lists in all five Step
verifiers. It confirmed {behavioral_checks} named cases:

{chr(10).join(f"- `{name}`: {count}" for name, count in counts.items())}

This number is conservative: dynamic or implicit assertions are not counted.
It is not evidence that the checks pass. Oracle, progressive Starter, five
Step-specific mutants, subprocess isolation, repeatability and Harbor jobs
must run downstream. Target-agent rollout count remains zero.
"""
    rubric = {
        "version": "1.0",
        "task_id": task_id,
        "review_type": "expert-review-only",
        "criteria": [
            {
                "id": "semantic_depth",
                "weight": 0.30,
                "checks": [
                    "Each Step adds material domain behavior.",
                    "Step 5 regresses Steps 1 through 4.",
                ],
            },
            {
                "id": "verifier_strength",
                "weight": 0.30,
                "checks": [
                    "Checks are black-box and subprocess-isolated.",
                    "Five deterministic mutants cover Steps 1 through 5.",
                ],
            },
            {
                "id": "contract_alignment",
                "weight": 0.20,
                "checks": [
                    "Instructions, public API and hidden checks agree.",
                    "No hidden check requires an undisclosed public name.",
                ],
            },
            {
                "id": "provenance_hygiene",
                "weight": 0.10,
                "checks": [
                    f"Source is {source_uri} under {source_license}.",
                    "No upstream code or proprietary data is copied.",
                ],
            },
            {
                "id": "calibration",
                "weight": 0.10,
                "checks": [
                    "Static quality is not represented as calibrated difficulty.",
                    "Cross-family repeated target-agent rollouts are required.",
                ],
            },
        ],
    }

    files = [
        _file("README.md", readme),
        _file("metadata.json", json.dumps(metadata, indent=2, sort_keys=True)),
        _file("task.toml", "\n".join(task_lines)),
        _file("environment/Dockerfile", dockerfile),
        _file("environment/knowledge/index.md", index_md),
        _file("environment/knowledge/public_api.md", "\n".join(public_md_parts)),
        _file(
            "environment/knowledge/public_api.json",
            json.dumps(public_api, indent=2, sort_keys=True),
        ),
        _file(
            "environment/knowledge/architecture.md",
            "\n".join(architecture_parts),
        ),
        _file(
            f"rubrics/{task_id}.yaml",
            json.dumps(rubric, indent=2, sort_keys=True),
        ),
        _file("review/provenance_notes.md", provenance_notes),
        _file("review/verifier_notes.md", verifier_notes),
    ]
    occupied = set(core_files) | set(verification_files)
    collisions = occupied & {item["path"] for item in files}
    if collisions:
        raise ValueError(f"compiled package paths already exist: {sorted(collisions)}")
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "fragment": "package",
        "files": files,
        "implementation_notes": [
            "Package files were deterministically compiled from accepted inputs.",
            f"Behavioral check count is the conservative AST count: {behavioral_checks}.",
        ],
        "known_open_gates": [
            "Oracle and progressive Starter audit not yet executed.",
            "Five Step-specific mutant rejections not yet executed.",
            "Harbor Oracle/Nop jobs not yet executed.",
            "Target-agent rollouts remain 0; difficulty is uncalibrated.",
            "Expert semantic and provenance approval is pending.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprint", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--core-fragment", type=Path, required=True)
    parser.add_argument("--verification-fragment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        fragment = compile_package_fragment(
            _load_json(args.blueprint),
            _load_json(args.contract),
            _load_json(args.core_fragment),
            _load_json(args.verification_fragment),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    atomic_json(args.output, fragment)
    print(
        json.dumps(
            {
                "task_id": fragment["task_id"],
                "file_count": len(fragment["files"]),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
