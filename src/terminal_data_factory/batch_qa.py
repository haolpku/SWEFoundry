from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from .multistep import validate_multistep_task


SCHEMA_VERSION = "1.0"
DEFAULT_LIMIT = 10
DEFAULT_REPEATS = 2
MAX_TEXT_BYTES = 2_000_000

SECRET_PATTERNS = {
    "openai_compatible_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_token": re.compile(
        r"(?i)\bauthorization\s*[:=]\s*bearer\s+(?!<REDACTED)[A-Za-z0-9._~+/=-]{16,}"
    ),
}
ENDPOINT_PATTERNS = {
    "ip_url": re.compile(
        r"(?i)\bhttps?://(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?(?:[/\s\"']|$)"
    ),
}
ABSOLUTE_PATH_PATTERNS = {
    "macos_user_path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    "linux_user_path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
    "windows_user_path": re.compile(
        r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[A-Za-z0-9._-]+[\\/]"
    ),
}


def discover_batch_tasks(root: Path, limit: int = DEFAULT_LIMIT) -> list[Path]:
    """Discover one task or direct tasks in a standalone batch directory."""
    root = root.resolve()
    if (root / "task.toml").is_file():
        tasks = [root]
    else:
        candidates: set[Path] = {
            path
            for path in root.iterdir()
            if path.is_dir() and (path / "task.toml").is_file()
        }
        for container_name in ("task", "tasks"):
            container = root / container_name
            if not container.is_dir():
                continue
            candidates.update(
                path
                for path in container.iterdir()
                if path.is_dir() and (path / "task.toml").is_file()
            )
        tasks = sorted(candidates, key=lambda path: path.name)
    if len(tasks) > limit:
        raise ValueError(f"batch contains {len(tasks)} tasks; limit is {limit}")
    return tasks


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix().encode()
        if path.is_symlink():
            digest.update(b"L\0" + relative + b"\0" + os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"F\0" + relative + b"\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_task(task: Path) -> dict[str, Any]:
    findings: dict[str, list[dict[str, Any]]] = {
        "secrets": [],
        "endpoints": [],
        "absolute_paths": [],
        "python_bytecode": [],
    }
    for path in sorted(task.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(task).as_posix()
        if path.is_dir():
            if path.name == "__pycache__":
                findings["python_bytecode"].append(
                    {"path": relative, "kind": "cache_directory"}
                )
            continue
        if not path.is_file():
            continue
        if path.suffix in {".pyc", ".pyo"}:
            findings["python_bytecode"].append(
                {"path": relative, "kind": "compiled_file"}
            )
        if path.stat().st_size > MAX_TEXT_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        pattern_groups = (
            ("secrets", SECRET_PATTERNS),
            ("endpoints", ENDPOINT_PATTERNS),
            ("absolute_paths", ABSOLUTE_PATH_PATTERNS),
        )
        for category, patterns in pattern_groups:
            for kind, pattern in patterns.items():
                for match in pattern.finditer(text):
                    findings[category].append(
                        {
                            "path": relative,
                            "line": _line_number(text, match.start()),
                            "kind": kind,
                        }
                    )
    counts = {name: len(items) for name, items in findings.items()}
    return {
        "passed": not any(counts.values()),
        "counts": counts,
        "findings": findings,
    }


def _audit_environment(temp_home: Path) -> dict[str, str]:
    temp_home.mkdir(parents=True, exist_ok=True)
    allowed = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(
        {
            "HOME": str(temp_home),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def _audit_failure_summary(report: Any, *, limit: int = 100) -> list[dict[str, Any]]:
    """Extract portable failure evidence from heterogeneous audit schemas."""
    failures: list[dict[str, Any]] = []

    def visit(value: Any, path: tuple[str, ...]) -> None:
        if len(failures) >= limit:
            return
        if isinstance(value, dict):
            failed = value.get("passed") is False or value.get("release_pass") == 0
            if failed:
                useful = {
                    key: item
                    for key, item in value.items()
                    if key
                    in {
                        "name",
                        "gate",
                        "step",
                        "position",
                        "mutant",
                        "passed",
                        "release_pass",
                        "correctness",
                        "expected_release_pass",
                        "observed_release_pass",
                        "checks_passed",
                        "checks_total",
                        "error",
                    }
                    and isinstance(item, (str, int, float, bool, type(None)))
                }
                failures.append(
                    {
                        "path": "/".join(path) or "$",
                        "detail": useful,
                    }
                )
            for key, item in value.items():
                visit(item, (*path, str(key)))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, (*path, str(index)))

    visit(report, ())
    return failures


def _run_audit_once(task: Path, timeout: int, run_number: int) -> dict[str, Any]:
    audit_script = task / "verifier/run_audit.py"
    if not audit_script.is_file():
        return {
            "run": run_number,
            "returncode": None,
            "report_present": False,
            "report_passed": False,
            "report_sha256": None,
            "error": "missing verifier/run_audit.py",
        }
    report_path = task / "verifier/audit-report.json"
    report_path.unlink(missing_ok=True)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(audit_script)],
            cwd=task,
            env=_audit_environment(task.parent / ".qa-home"),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "run": run_number,
            "returncode": None,
            "report_present": False,
            "report_passed": False,
            "report_sha256": None,
            "error": f"audit timed out after {timeout}s",
        }
    report_present = report_path.is_file()
    report_sha256 = None
    report_passed = False
    report_top_level_keys: list[str] = []
    failure_summary: list[dict[str, Any]] = []
    error = None
    if report_present:
        raw = report_path.read_bytes()
        report_sha256 = hashlib.sha256(raw).hexdigest()
        try:
            report = json.loads(raw)
            if isinstance(report, dict):
                report_passed = report.get("passed") is True
                report_top_level_keys = sorted(str(key) for key in report)
                failure_summary = _audit_failure_summary(report)
            else:
                error = "audit-report.json top level is not an object"
        except (json.JSONDecodeError, UnicodeDecodeError):
            error = "audit-report.json is not valid JSON"
    else:
        error = "audit did not produce verifier/audit-report.json"
    return {
        "run": run_number,
        "returncode": completed.returncode,
        "report_present": report_present,
        "report_passed": report_passed,
        "report_sha256": report_sha256,
        "report_top_level_keys": report_top_level_keys,
        "failure_summary": failure_summary,
        "error": error,
    }


def _audit_copy(task: Path, repeats: int, timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"tdf-batch-qa-{task.name}-") as raw:
        runs = []
        for number in range(1, repeats + 1):
            copied_task = Path(raw) / f"run-{number}" / task.name
            copied_task.parent.mkdir()
            shutil.copytree(
                task,
                copied_task,
                symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            runs.append(
                _run_audit_once(
                    copied_task,
                    timeout=timeout,
                    run_number=number,
                )
            )
    hashes = [run["report_sha256"] for run in runs]
    deterministic = (
        len(hashes) == repeats
        and all(value is not None for value in hashes)
        and len(set(hashes)) == 1
    )
    passed = deterministic and all(
        run["returncode"] == 0 and run["report_passed"] for run in runs
    )
    return {
        "passed": passed,
        "repeats": repeats,
        "deterministic": deterministic,
        "unique_report_hashes": sorted(
            value for value in set(hashes) if value is not None
        ),
        "runs": runs,
    }


def _completed_detail(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-1000:],
        "stderr_tail": completed.stderr[-1000:],
    }


def _failed_check_evidence(reward: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    """Read verifier-owned evidence and retain only failed named checks."""
    evidence_path = reward / "evidence.json"
    if not evidence_path.is_file():
        return []
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    raw_checks = evidence.get("checks", evidence.get("cases", []))
    if not isinstance(raw_checks, list):
        return []
    failures: list[dict[str, Any]] = []
    for item in raw_checks:
        if not isinstance(item, dict) or item.get("passed") is not False:
            continue
        failures.append(
            {
                key: value
                for key, value in item.items()
                if key in {"name", "returncode", "stdout", "stderr", "error"}
                and isinstance(value, (str, int, float, bool, type(None)))
            }
        )
        if len(failures) >= limit:
            break
    return failures


def _progressive_oracle_copy(task: Path, timeout: int) -> dict[str, Any]:
    """Independently install Steps 1..N, then run public smoke and verifier.

    This deliberately does not call ``verifier/run_audit.py``. It prevents a
    task-owned audit runner from substituting the final solution for an
    intermediate Step or otherwise masking a broken cumulative reference
    solution.
    """

    task = task.resolve()
    config = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
    step_names = [entry.get("name") for entry in config.get("steps", [])]
    if (
        len(step_names) != 5
        or any(not isinstance(name, str) or not name for name in step_names)
    ):
        return {
            "passed": False,
            "steps_passed": 0,
            "steps": [],
            "error": "task.toml does not declare five named Steps",
        }
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(
        prefix=f"tdf-progressive-oracle-{task.name}-"
    ) as raw:
        base = Path(raw)
        for position, step_name in enumerate(step_names, 1):
            run_root = base / f"step-{position}"
            workspace = run_root / "workspace"
            codebase = workspace / "environment/codebase"
            codebase.parent.mkdir(parents=True)
            shutil.copytree(
                task / "environment/codebase",
                codebase,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            shutil.copytree(
                task / "steps",
                workspace / "steps",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            shutil.copytree(
                task / "verifier",
                workspace / "verifier",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            reward = run_root / "reward"
            env = _audit_environment(run_root / "home")
            env.update(
                {
                    "TDF_WORKSPACE": str(workspace),
                    "TDF_REWARD_DIR": str(reward),
                    "TDF_PYTHON": sys.executable,
                }
            )
            installs: list[dict[str, Any]] = []
            install_ok = True
            for prior_name in step_names[:position]:
                solve = task / "steps" / prior_name / "solution/solve.sh"
                if not solve.is_file():
                    installs.append(
                        {
                            "step": prior_name,
                            "returncode": None,
                            "error": "missing solution/solve.sh",
                        }
                    )
                    install_ok = False
                    break
                try:
                    completed = subprocess.run(
                        [str(solve)],
                        cwd=task,
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired:
                    installs.append(
                        {
                            "step": prior_name,
                            "returncode": None,
                            "error": f"solution timed out after {timeout}s",
                        }
                    )
                    install_ok = False
                    break
                installs.append({"step": prior_name, **_completed_detail(completed)})
                if completed.returncode != 0:
                    install_ok = False
                    break

            smoke_path = (
                codebase / "public_contract_tests" / f"step_{position:02d}_smoke.py"
            )
            smoke_detail: dict[str, Any]
            if install_ok and smoke_path.is_file():
                try:
                    completed = subprocess.run(
                        [sys.executable, "-B", "-I", str(smoke_path)],
                        cwd=codebase,
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=timeout,
                    )
                    smoke_detail = _completed_detail(completed)
                except subprocess.TimeoutExpired:
                    smoke_detail = {
                        "returncode": None,
                        "error": f"public smoke timed out after {timeout}s",
                    }
            else:
                smoke_detail = {
                    "returncode": None,
                    "error": (
                        "prior solution failed"
                        if not install_ok
                        else "missing public smoke"
                    ),
                }

            verifier_detail: dict[str, Any]
            verifier = task / "steps" / step_name / "tests/test.sh"
            if install_ok and verifier.is_file():
                verifier_env = dict(env)
                verifier_source = (
                    task / "steps" / step_name / "tests/verifier.py"
                ).read_text(encoding="utf-8")
                shell_source = verifier.read_text(encoding="utf-8")
                if "TDF_TESTS_DIR" in verifier_source:
                    tests_dir = task
                elif re.search(
                    r"\$[{]?TDF_TESTS_DIR[}]?/verifier\.py",
                    shell_source,
                ):
                    tests_dir = task / "steps" / step_name / "tests"
                else:
                    tests_dir = workspace / ".tdf-tests"
                verifier_env["TDF_TESTS_DIR"] = str(tests_dir)
                try:
                    completed = subprocess.run(
                        [str(verifier)],
                        cwd=task,
                        env=verifier_env,
                        text=True,
                        capture_output=True,
                        timeout=timeout,
                    )
                    verifier_detail = _completed_detail(completed)
                except subprocess.TimeoutExpired:
                    verifier_detail = {
                        "returncode": None,
                        "error": f"verifier timed out after {timeout}s",
                    }
            else:
                verifier_detail = {
                    "returncode": None,
                    "error": (
                        "prior solution failed"
                        if not install_ok
                        else "missing tests/test.sh"
                    ),
                }
            reward_path = reward / "reward.json"
            metrics: dict[str, Any] = {}
            if reward_path.is_file():
                try:
                    loaded = json.loads(reward_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        metrics = loaded
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            failed_checks = _failed_check_evidence(reward)
            step_passed = (
                install_ok
                and smoke_detail.get("returncode") == 0
                and verifier_detail.get("returncode") == 0
                and metrics.get("release_pass") == 1
                and metrics.get("correctness") == 1.0
            )
            results.append(
                {
                    "position": position,
                    "step": step_name,
                    "passed": step_passed,
                    "installs": installs,
                    "public_smoke": smoke_detail,
                    "verifier": verifier_detail,
                    "metrics": metrics,
                    "failed_checks": failed_checks,
                }
            )
    return {
        "passed": len(results) == 5 and all(item["passed"] for item in results),
        "steps_passed": sum(item["passed"] for item in results),
        "steps": results,
    }


def _literal_case_names(node: ast.AST) -> list[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
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
        elif (
            isinstance(item, (ast.List, ast.Tuple))
            and item.elts
            and isinstance(item.elts[0], ast.Constant)
        ):
            name = item.elts[0].value
        elif (
            isinstance(item, ast.Call)
            and item.args
            and isinstance(item.args[0], ast.Constant)
        ):
            name = item.args[0].value
        if not isinstance(name, str) or not name.strip():
            return None
        names.append(name)
    if len(set(names)) != len(names):
        return None
    return names


def _shared_case_registry(task: Path) -> dict[str, list[str]]:
    registry: dict[str, list[str]] = {}
    for path in sorted((task / "verifier").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                variable = next(
                    (
                        target.id
                        for target in targets
                        if isinstance(target, ast.Name)
                        and target.id in {"CHECKS", "_STEP_CHECKS"}
                    ),
                    None,
                )
                if variable and isinstance(node.value, ast.Dict):
                    for key, value in zip(node.value.keys, node.value.values):
                        if not (
                            isinstance(key, ast.Constant)
                            and isinstance(key.value, str)
                        ):
                            continue
                        names = _literal_case_names(value)
                        if names is not None:
                            registry[key.value] = names
            if not isinstance(node, ast.FunctionDef):
                continue
            if re.fullmatch(r"step[1-5]_cases", node.name):
                returns = [
                    statement
                    for statement in node.body
                    if isinstance(statement, ast.Return)
                ]
                if len(returns) == 1 and returns[0].value is not None:
                    names = _literal_case_names(returns[0].value)
                    if names is not None:
                        registry[f"factory:{node.name}"] = names
            if node.name == "step_checks" and node.args.args:
                parameter = node.args.args[0].arg
                for branch in node.body:
                    if not isinstance(branch, ast.If):
                        continue
                    test = branch.test
                    if not (
                        isinstance(test, ast.Compare)
                        and isinstance(test.left, ast.Name)
                        and test.left.id == parameter
                        and len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Eq)
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and isinstance(test.comparators[0].value, int)
                    ):
                        continue
                    returns = [
                        statement
                        for statement in branch.body
                        if isinstance(statement, ast.Return)
                    ]
                    if len(returns) == 1 and returns[0].value is not None:
                        names = _literal_case_names(returns[0].value)
                        if names is not None:
                            registry[
                                f"position:{test.comparators[0].value}"
                            ] = names
    return registry


def _step_case_names(
    verifier: Path,
    position: int,
    shared: dict[str, list[str]],
) -> list[str]:
    tree = ast.parse(verifier.read_text(encoding="utf-8"), filename=str(verifier))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id in {"CASES", "CHECKS"}
            for target in targets
        ):
            continue
        if node.value is not None:
            names = _literal_case_names(node.value)
            if names is not None:
                return names
    direct: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        append = node.value
        if not (
            isinstance(append.func, ast.Attribute)
            and append.func.attr == "append"
            and append.args
            and isinstance(append.args[0], ast.Call)
        ):
            continue
        call = append.args[0]
        if (
            call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            direct.append(call.args[0].value)
    if direct and len(set(direct)) == len(direct):
        return direct
    keys: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "CHECKS"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.append(node.slice.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if (
                node.func.id == "get_checks"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                keys.append(node.args[0].value)
            if node.func.id == "run_verification":
                keys.append(f"position:{position}")
            if re.fullmatch(r"step[1-5]_cases", node.func.id):
                keys.append(f"factory:{node.func.id}")
    matched = {key: shared[key] for key in keys if key in shared}
    if len(matched) != 1:
        raise ValueError(
            f"{verifier}: cannot resolve exactly one static case registry"
        )
    return next(iter(matched.values()))


def _independent_inventory(task: Path) -> dict[str, Any]:
    task = task.resolve()
    config = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
    step_names = [entry.get("name") for entry in config.get("steps", [])]
    shared = _shared_case_registry(task)
    by_step: dict[str, int] = {}
    case_names: dict[str, list[str]] = {}
    errors: list[str] = []
    for position, step_name in enumerate(step_names, 1):
        verifier = task / "steps" / str(step_name) / "tests/verifier.py"
        try:
            names = _step_case_names(verifier, position, shared)
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"Step {position}: {type(exc).__name__}")
            names = []
        by_step[str(step_name)] = len(names)
        case_names[str(step_name)] = names
    behavioral_checks = sum(by_step.values())
    metadata = json.loads((task / "metadata.json").read_text(encoding="utf-8"))
    declared_checks = metadata.get("quality", {}).get("behavioral_checks")
    mutants = sorted((task / "verifier/anti_cheat").glob("fp*.py"))
    mutant_steps = sorted(
        {
            int(match.group(1))
            for path in mutants
            if (match := re.match(r"fp([1-5])", path.name))
        }
    )
    public_smokes = sorted(
        (task / "environment/codebase/public_contract_tests").glob(
            "step_*_smoke.py"
        )
    )
    passed = (
        len(step_names) == 5
        and not errors
        and behavioral_checks == declared_checks
        and behavioral_checks >= 30
        and len(mutants) == 5
        and mutant_steps == [1, 2, 3, 4, 5]
        and len(public_smokes) == 5
    )
    return {
        "passed": passed,
        "behavioral_checks": behavioral_checks,
        "declared_behavioral_checks": declared_checks,
        "behavioral_checks_by_step": by_step,
        "case_names_by_step": case_names,
        "mutants": len(mutants),
        "mutant_steps": mutant_steps,
        "public_smokes": len(public_smokes),
        "errors": errors,
    }


def run_batch_qa(
    root: Path,
    *,
    limit: int = DEFAULT_LIMIT,
    repeats: int = DEFAULT_REPEATS,
    timeout: int = 180,
) -> dict[str, Any]:
    if repeats < 2:
        raise ValueError("repeats must be at least 2")
    if limit < 1 or limit > DEFAULT_LIMIT:
        raise ValueError(f"limit must be between 1 and {DEFAULT_LIMIT}")
    tasks = discover_batch_tasks(root, limit=limit)
    results = []
    for task in tasks:
        before = _tree_digest(task)
        try:
            static_report = validate_multistep_task(task, require_evidence=False)
            static = {
                "passed": static_report.passed,
                "errors": static_report.errors,
                "warnings": static_report.warnings,
            }
        except Exception as exc:  # QA should report a malformed task, not abort the batch.
            static = {
                "passed": False,
                "errors": [f"validator raised {type(exc).__name__}"],
                "warnings": [],
            }
        scan = scan_task(task)
        try:
            audit = _audit_copy(task, repeats=repeats, timeout=timeout)
        except Exception as exc:  # Preserve results for the other tasks in the batch.
            audit = {
                "passed": False,
                "repeats": repeats,
                "deterministic": False,
                "unique_report_hashes": [],
                "runs": [],
                "error": f"audit runner raised {type(exc).__name__}",
            }
        try:
            progressive_oracle = _progressive_oracle_copy(task, timeout=timeout)
        except Exception as exc:
            progressive_oracle = {
                "passed": False,
                "steps_passed": 0,
                "steps": [],
                "error": f"progressive Oracle raised {type(exc).__name__}",
            }
        try:
            inventory = _independent_inventory(task)
        except Exception as exc:
            inventory = {
                "passed": False,
                "behavioral_checks": 0,
                "mutants": 0,
                "public_smokes": 0,
                "errors": [f"inventory raised {type(exc).__name__}"],
            }
        after = _tree_digest(task)
        source_unchanged = before == after
        passed = (
            static["passed"]
            and scan["passed"]
            and audit["passed"]
            and progressive_oracle["passed"]
            and inventory["passed"]
            and source_unchanged
        )
        results.append(
            {
                "task_id": task.name,
                "passed": passed,
                "static_validation": static,
                "audit": audit,
                "progressive_oracle": progressive_oracle,
                "independent_inventory": inventory,
                "scan": scan,
                "source_unchanged": source_unchanged,
                "source_sha256": before,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "batch_name": root.resolve().name,
        "task_limit": limit,
        "task_count": len(results),
        "passed": bool(results) and all(item["passed"] for item in results),
        "totals": {
            "static_passed": sum(
                item["static_validation"]["passed"] for item in results
            ),
            "audit_passed": sum(item["audit"]["passed"] for item in results),
            "progressive_oracle_passed": sum(
                item["progressive_oracle"]["passed"] for item in results
            ),
            "progressive_oracle_steps_passed": sum(
                item["progressive_oracle"]["steps_passed"] for item in results
            ),
            "independent_inventory_passed": sum(
                item["independent_inventory"]["passed"] for item in results
            ),
            "behavioral_checks_confirmed": sum(
                item["independent_inventory"]["behavioral_checks"]
                for item in results
            ),
            "mutants_confirmed": sum(
                item["independent_inventory"]["mutants"] for item in results
            ),
            "public_smokes_confirmed": sum(
                item["independent_inventory"]["public_smokes"]
                for item in results
            ),
            "deterministic_audits": sum(
                item["audit"]["deterministic"] for item in results
            ),
            "clean_scans": sum(item["scan"]["passed"] for item in results),
            "sources_unchanged": sum(item["source_unchanged"] for item in results),
        },
        "tasks": results,
    }


def write_summary(summary: dict[str, Any], output: Path, source_root: Path) -> None:
    output = output.resolve()
    source_root = source_root.resolve()
    if output == source_root or source_root in output.parents:
        raise ValueError("output must be outside the source batch directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        delete=False,
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only QA for up to ten standalone multi-step tasks"
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--timeout", type=int, default=180)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_batch_qa(
        args.root,
        limit=args.limit,
        repeats=args.repeats,
        timeout=args.timeout,
    )
    if args.output:
        write_summary(summary, args.output, args.root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
