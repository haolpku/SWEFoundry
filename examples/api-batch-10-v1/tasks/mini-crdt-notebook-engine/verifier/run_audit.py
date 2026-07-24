#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODEBASE = ROOT / "environment" / "codebase"
REPORT = ROOT / "verifier" / "audit-report.json"
STEPS = [
    ("step-1", "1-parse-immutable-operations"),
    ("step-2", "2-validate-causal-dag"),
    ("step-3", "3-merge-notebook-text-deterministically"),
    ("step-4", "4-compute-frontiers-and-compaction-plan"),
    ("step-5", "5-integrated-notebook-recovery-and-migration"),
]
MUTANTS = [
    ("step-1", "fp1_last_duplicate_wins.py"),
    ("step-2", "fp2_allows_missing_dependency.py"),
    ("step-3", "fp3_input_order_concurrency.py"),
    ("step-4", "fp4_compacts_unacknowledged.py"),
    ("step-5", "fp5_merges_before_dag_validation.py"),
]


def _env(
    workspace: pathlib.Path,
    reward: pathlib.Path,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["TDF_WORKSPACE"] = str(workspace)
    env["TDF_TESTS_DIR"] = str(ROOT)
    env["TDF_REWARD_DIR"] = str(reward)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
    return env


def _workspace(tmp_root: pathlib.Path) -> pathlib.Path:
    workspace = tmp_root / "workspace"
    target = workspace / "environment" / "codebase"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CODEBASE, target)
    return workspace


def _run(
    command: list[str],
    cwd: pathlib.Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )


def _solve(workspace: pathlib.Path, step_dir: str) -> bool:
    solve = ROOT / "steps" / step_dir / "solution" / "solve.sh"
    result = _run(
        [str(solve)],
        ROOT,
        _env(workspace, workspace / "_solve_reward"),
    )
    return result.returncode == 0


def _install_through(workspace: pathlib.Path, step_index: int) -> bool:
    for _, step_dir in STEPS[: step_index + 1]:
        if not _solve(workspace, step_dir):
            return False
    return True


def _run_verifier(
    workspace: pathlib.Path,
    step_id: str,
    step_dir: str,
    label: str,
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    reward = workspace / "_reward" / label
    test_sh = ROOT / "steps" / step_dir / "tests" / "test.sh"
    process = _run(
        [str(test_sh)],
        ROOT,
        _env(workspace, reward, extra_env),
    )
    reward_file = reward / "reward.json"
    metrics = {}
    if reward_file.exists():
        metrics = json.loads(reward_file.read_text(encoding="utf-8"))
    return {
        "exit_code": process.returncode,
        "release_pass": metrics.get("release_pass"),
        "correctness": metrics.get("correctness"),
        "reward_keys": sorted(metrics.keys()),
    }


def _gate(
    name: str,
    passed: bool,
    detail: dict[str, object] | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {"name": name, "passed": bool(passed)}
    if detail is not None:
        item["detail"] = detail
    return item


def _starter_gate(
    step_index: int,
    step_id: str,
    step_dir: str,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="tdf-audit-") as raw:
        workspace = _workspace(pathlib.Path(raw))
        prior_installed = all(
            _solve(workspace, prior_dir)
            for _, prior_dir in STEPS[:step_index]
        )
        result = _run_verifier(
            workspace, step_id, step_dir, f"starter-{step_id}"
        )
        passed = prior_installed and result.get("release_pass") == 0
        return _gate(
            f"{step_id}:starter_release_pass_is_zero", passed, result
        )


def _oracle_gate(
    step_index: int,
    step_id: str,
    step_dir: str,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="tdf-audit-") as raw:
        workspace = _workspace(pathlib.Path(raw))
        installed = _install_through(workspace, step_index)
        result = _run_verifier(
            workspace, step_id, step_dir, f"oracle-{step_id}"
        )
        passed = (
            installed
            and result.get("release_pass") == 1
            and result.get("correctness") == 1.0
        )
        return _gate(
            f"{step_id}:cumulative_oracle_release_pass_is_one",
            passed,
            result,
        )


def _public_smoke_gate(step_index: int, step_id: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="tdf-audit-") as raw:
        workspace = _workspace(pathlib.Path(raw))
        installed = _install_through(workspace, step_index)
        smoke = (
            workspace
            / "environment"
            / "codebase"
            / "public_contract_tests"
            / f"step_{step_index + 1:02d}_smoke.py"
        )
        process = _run(
            [sys.executable, "-I", str(smoke)],
            workspace / "environment" / "codebase",
            _env(workspace, workspace / "_public_smoke_reward"),
        )
        detail = {
            "installed": installed,
            "exit_code": process.returncode,
        }
        return _gate(
            f"{step_id}:cumulative_public_smoke_passes",
            installed and process.returncode == 0,
            detail,
        )


def _mutant_gate(step_id: str, mutant: str) -> dict[str, object]:
    step_dir = dict(STEPS)[step_id]
    with tempfile.TemporaryDirectory(prefix="tdf-audit-") as raw:
        workspace = _workspace(pathlib.Path(raw))
        installed = _install_through(workspace, 4)
        process = _run(
            [str(ROOT / "verifier" / "anti_cheat" / mutant)],
            ROOT,
            _env(workspace, workspace / "_mutant_reward"),
        )
        result = _run_verifier(
            workspace, step_id, step_dir, f"mutant-{step_id}"
        )
        passed = (
            installed
            and process.returncode == 0
            and result.get("release_pass") == 0
        )
        detail = {
            "mutant_exit_code": process.returncode,
            "release_pass": result.get("release_pass"),
            "correctness": result.get("correctness"),
        }
        return _gate(
            f"{step_id}:{mutant}:mutant_release_pass_is_zero",
            passed,
            detail,
        )


def _isolation_gate() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="tdf-audit-") as raw:
        base = pathlib.Path(raw)
        workspace = _workspace(base)
        installed = _install_through(workspace, 4)
        (
            workspace
            / "environment"
            / "codebase"
            / "sitecustomize.py"
        ).write_text("raise SystemExit(77)\n", encoding="utf-8")
        poison = base / "poison"
        package = poison / "crdtnotebook"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            "raise SystemExit(88)\n", encoding="utf-8"
        )
        result = _run_verifier(
            workspace,
            "step-1",
            "1-parse-immutable-operations",
            "isolation",
            {"PYTHONPATH": str(poison), "PYTHONHOME": str(poison)},
        )
        passed = installed and result.get("release_pass") == 1
        return _gate(
            "python_isolation_ignores_sitecustomize_pythonpath_pythonhome",
            passed,
            result,
        )


def main() -> int:
    gates: list[dict[str, object]] = []
    for index, (step_id, step_dir) in enumerate(STEPS):
        gates.append(_starter_gate(index, step_id, step_dir))
        gates.append(_oracle_gate(index, step_id, step_dir))
        gates.append(_public_smoke_gate(index, step_id))
    for step_id, mutant in MUTANTS:
        gates.append(_mutant_gate(step_id, mutant))
    gates.append(_isolation_gate())
    gates = sorted(gates, key=lambda item: str(item["name"]))
    report = {
        "schema_version": "1.0",
        "task_id": "mini-crdt-notebook-engine",
        "passed": all(bool(gate["passed"]) for gate in gates),
        "summary": {
            "gates": len(gates),
            "gates_passed": sum(bool(gate["passed"]) for gate in gates),
            "cumulative_oracle_steps": 5,
            "cumulative_public_smokes": 5,
            "starter_steps": 5,
            "step_mutants": 5,
            "isolation_probes": 1,
        },
        "gates": gates,
    }
    REPORT.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
