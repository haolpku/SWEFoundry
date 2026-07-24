#!/usr/bin/env python3
"""Repair CRDT progressive solutions and replace its self-referential audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TASK_ID = "mini-crdt-notebook-engine"
STEP_DIRS = (
    "1-parse-immutable-operations",
    "2-validate-causal-dag",
    "3-merge-notebook-text-deterministically",
    "4-compute-frontiers-and-compaction-plan",
    "5-integrated-notebook-recovery-and-migration",
)
MERGE_STUB = """def merge_notebook_text(ops: list[NotebookOp]) -> list[NotebookCell]:
    return []
"""
PLAN_STUB = """def plan_notebook_compaction(ops: list[NotebookOp], peer_frontiers: dict[str, list[str]]) -> CrdtCompactionPlan:
    return CrdtCompactionPlan()
"""


def _file_map(payload: dict) -> dict[str, dict]:
    return {item["path"]: item for item in payload["files"]}


def _init_source(position: int) -> str:
    names = [
        "CrdtNotebookError",
        "NotebookParseError",
        "NotebookValidationError",
        "NotebookOp",
        "parse_notebook_ops",
    ]
    if position >= 2:
        names.extend(["CrdtProblem", "validate_notebook_dag"])
    if position >= 3:
        names.extend(["NotebookCell", "merge_notebook_text"])
    if position >= 4:
        names.extend(["CrdtCompactionPlan", "plan_notebook_compaction"])
    if position >= 5:
        names.extend(["CrdtNotebookAuditReport", "audit_crdt_notebook"])
    exception_names = {
        "CrdtNotebookError",
        "NotebookParseError",
        "NotebookValidationError",
    }
    engine_names = [name for name in names if name not in exception_names]
    imports = (
        "from .exceptions import CrdtNotebookError, NotebookParseError, "
        "NotebookValidationError\n"
        "from .engine import (\n"
        + "".join(f"    {name},\n" for name in engine_names)
        + ")\n\n"
    )
    exports = "__all__ = [\n" + "".join(
        f'    "{name}",\n' for name in sorted(names)
    ) + "]\n"
    return imports + exports


def _upsert(files: list[dict], path: str, content: str, executable: bool = False) -> None:
    matches = [item for item in files if item["path"] == path]
    if len(matches) > 1:
        raise ValueError(f"duplicate path: {path}")
    value = {
        "path": path,
        "executable": executable,
        "content": content.rstrip() + "\n",
    }
    if matches:
        matches[0].update(value)
    else:
        files.append(value)


AUDIT_SOURCE = r'''#!/usr/bin/env python3
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
'''


def repair(core_input: Path, verification_input: Path, core_output: Path, verification_output: Path, record: Path) -> None:
    core = json.loads(core_input.read_text(encoding="utf-8"))
    verification = json.loads(verification_input.read_text(encoding="utf-8"))
    if core.get("task_id") != TASK_ID or core.get("fragment") != "core":
        raise ValueError("unexpected core fragment")
    if (
        verification.get("task_id") != TASK_ID
        or verification.get("fragment") != "verification"
    ):
        raise ValueError("unexpected verification fragment")

    core_files = _file_map(core)
    step2_path = (
        "steps/2-validate-causal-dag/solution/files/crdtnotebook/engine.py"
    )
    generated_step3_path = (
        "steps/3-merge-notebook-text-deterministically/"
        "solution/files/crdtnotebook/engine.py"
    )
    generated_step4_path = (
        "steps/4-compute-frontiers-and-compaction-plan/"
        "solution/files/crdtnotebook/engine.py"
    )
    step2 = core_files[step2_path]["content"]
    generated_step3 = core_files[generated_step3_path]["content"]
    generated_step4 = core_files[generated_step4_path]["content"]
    merge_impl = generated_step3[generated_step3.index("def merge_notebook_text") :]
    closure_and_plan = generated_step4[generated_step4.index("def _closure") :]
    if MERGE_STUB not in step2:
        raise ValueError("Step 2 merge stub not found")
    step3 = step2.replace(MERGE_STUB, merge_impl.rstrip() + "\n", 1)
    if PLAN_STUB not in step3:
        raise ValueError("Step 3 plan stub not found")
    step4 = step3.replace(PLAN_STUB, closure_and_plan.rstrip() + "\n", 1)
    core_files[generated_step3_path]["content"] = step3
    core_files[generated_step4_path]["content"] = step4

    core_files["environment/codebase/crdtnotebook/__init__.py"]["content"] = (
        "from .exceptions import CrdtNotebookError, NotebookParseError, "
        "NotebookValidationError\n\n"
        "__all__ = [\n"
        '    "CrdtNotebookError",\n'
        '    "NotebookParseError",\n'
        '    "NotebookValidationError",\n'
        "]\n"
    )
    for position, step_dir in enumerate(STEP_DIRS, 1):
        _upsert(
            core["files"],
            f"steps/{step_dir}/solution/files/crdtnotebook/__init__.py",
            _init_source(position),
        )
        solve = f"""#!/usr/bin/env sh
set -eu
ROOT="${{TDF_WORKSPACE:-$(pwd)}}"
DST="$ROOT/environment/codebase/crdtnotebook"
mkdir -p "$DST"
cp "$(dirname "$0")/files/crdtnotebook/engine.py" "$DST/engine.py"
cp "$(dirname "$0")/files/crdtnotebook/__init__.py" "$DST/__init__.py"
python3 -m py_compile "$DST/engine.py" "$DST/__init__.py"
"""
        _upsert(
            core["files"],
            f"steps/{step_dir}/solution/solve.sh",
            solve,
            executable=True,
        )

    _upsert(
        verification["files"],
        "verifier/run_audit.py",
        AUDIT_SOURCE,
        executable=True,
    )
    note = (
        "P0 repair: progressive Step 3/4 solutions are full cumulative modules; "
        "package exports advance by Step; audit independently installs Steps "
        "1..N and runs each public smoke plus strict verifier."
    )
    for payload in (core, verification):
        notes = payload.setdefault("implementation_notes", [])
        if note not in notes:
            notes.append(note)
    core_output.write_text(
        json.dumps(core, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    verification_output.write_text(
        json.dumps(verification, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    record.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "task_id": TASK_ID,
                "kind": "p0-progressive-oracle-repair",
                "reproduced_before_fix": {
                    "cumulative_steps_passed": 3,
                    "cumulative_steps_total": 5,
                    "failed_steps": [3, 4],
                    "step_3_correctness": 0.0,
                    "step_4_correctness": 0.0,
                },
                "changes": [
                    "Replace Step 3 patch-only engine with cumulative Step 1-3 module.",
                    "Replace Step 4 patch-only engine with cumulative Step 1-4 module.",
                    "Use progressive package __init__.py exports for Starter and Steps 1-5.",
                    "Make every solve.sh install engine.py and __init__.py.",
                    "Replace final-solution substitution with Step 1..N cumulative audit.",
                    "Add five cumulative public-smoke gates to task audit.",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-input", type=Path, required=True)
    parser.add_argument("--verification-input", type=Path, required=True)
    parser.add_argument("--core-output", type=Path, required=True)
    parser.add_argument("--verification-output", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    repair(
        args.core_input,
        args.verification_input,
        args.core_output,
        args.verification_output,
        args.record,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
