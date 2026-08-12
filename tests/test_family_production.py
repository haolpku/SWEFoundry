from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from terminal_data_factory.families.nl2repo import NL2RepoFamily
from terminal_data_factory.families.production import HarborBuildSpec, compile_harbor_task
from terminal_data_factory.families.swe_bench import SWEBenchFamily
from terminal_data_factory.families.swe_mutation import generate_swe_mutations
from terminal_data_factory.families.terminal_recipe import generate_terminal_tasks
from terminal_data_factory.production_qa import audit_production_task


VERIFIER = '''from __future__ import annotations
import json, os
from pathlib import Path
workspace = Path(os.environ["SWEFOUNDRY_WORKSPACE"])
passed = (workspace / "answer.txt").read_text().strip() == "42" if (workspace / "answer.txt").is_file() else False
reward = 1.0 if passed else 0.0
out = Path(os.environ["SWEFOUNDRY_REWARD_DIR"]); out.mkdir(parents=True, exist_ok=True)
(out / "reward.txt").write_text(f"{reward:.6f}\\n")
(out / "reward.json").write_text(json.dumps({"reward": reward, "passed": passed}))
'''


def _audit(task: Path, tmp_path: Path) -> tuple[float, float]:
    workspace = tmp_path / "workspace"
    reward_dir = tmp_path / "reward"
    workspace.mkdir(parents=True)
    for relative in (task / "environment/codebase").rglob("*"):
        if relative.is_file():
            target = workspace / relative.relative_to(task / "environment/codebase")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(relative.read_bytes())
    env = {**os.environ, "SWEFOUNDRY_WORKSPACE": str(workspace), "SWEFOUNDRY_REWARD_DIR": str(reward_dir), "SWEFOUNDRY_TEST_ROOT": str(task / "tests")}
    subprocess.run(["sh", str(task / "tests/test.sh")], check=True, env=env)
    starter = float((reward_dir / "reward.txt").read_text())
    subprocess.run(["sh", str(task / "solution/solve.sh")], check=True, env=env)
    subprocess.run(["sh", str(task / "tests/test.sh")], check=True, env=env)
    oracle = float((reward_dir / "reward.txt").read_text())
    return starter, oracle


def test_generic_compiler_creates_auditable_harbor_task(tmp_path: Path) -> None:
    task = compile_harbor_task(HarborBuildSpec(
        task_id="write-answer",
        family="terminal-bench",
        instruction="Write the required answer to /app/workspace/answer.txt.",
        starter_files={"README.md": "starter\n"},
        solution_files={"answer.txt": "42\n"},
        verifier_files={"verifier.py": VERIFIER},
    ), tmp_path / "tasks")
    assert _audit(task, tmp_path / "audit") == (0.0, 1.0)
    assert audit_production_task(task)["passed"] is True


def test_compiler_rejects_path_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe relative path"):
        compile_harbor_task(HarborBuildSpec(
            task_id="bad-path", family="terminal-bench", instruction="bad",
            starter_files={"../escape": "bad"}, solution_files={}, verifier_files={"verifier.py": VERIFIER},
        ), tmp_path)


def test_terminal_recipe_generator(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe.jsonl"
    recipe.write_text(json.dumps({
        "task_id": "terminal-answer", "family": "terminal-bench", "instruction": "Write answer.txt.",
        "starter_files": {}, "solution_files": {"answer.txt": "42\n"}, "verifier_files": {"verifier.py": VERIFIER},
    }) + "\n")
    assert len(generate_terminal_tasks(recipe, tmp_path / "tasks")) == 1


def test_nl2repo_packaging_enforces_independent_generation_runs(tmp_path: Path) -> None:
    source = tmp_path / "nl2repo.jsonl"
    row = {
        "task_id": "repo-answer", "instruction": "Build a repository that writes answer.txt.",
        "contract": {"answer": "42"}, "starter_files": {"README.md": "implement me\n"},
        "reference_files": {"answer.txt": "42\n"}, "hidden_test_files": {"verifier.py": VERIFIER},
        "provenance": {"contract_run_id": "run-a", "solution_run_id": "run-b", "verifier_run_id": "run-c"},
    }
    source.write_text(json.dumps(row) + "\n")
    tasks = NL2RepoFamily().package_for_harbor(source, tmp_path / "tasks", source_ref="local://nl2repo", dataset_version="1")
    assert _audit(tasks[0], tmp_path / "audit") == (0.0, 1.0)
    row["provenance"]["verifier_run_id"] = "run-b"
    source.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="must be non-empty and distinct"):
        NL2RepoFamily().package_for_harbor(source, tmp_path / "bad", source_ref="local://nl2repo", dataset_version="1")


def test_swe_mutation_and_runtime_packaging(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "calc.py"], check=True)
    subprocess.run([
        "git", "-C", str(repo), "-c", "user.name=SWEFoundry", "-c", "user.email=test@example.com",
        "commit", "-qm", "fixture",
    ], check=True)
    base_commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, text=True, capture_output=True,
    ).stdout.strip()
    recipes = tmp_path / "recipes.jsonl"
    recipes.write_text(json.dumps({
        "task_id": "demo-calc-add", "repo_url": "https://github.com/demo/calc", "base_commit": base_commit,
        "instruction": "Fix add so it returns the sum.", "test_command": "python -m pytest -q {test}",
        "fail_to_pass": ["tests/test_calc.py::test_add"], "pass_to_pass": ["tests/test_calc.py::test_sub"],
        "mutation": {"name": "wrong-operator", "path": "calc.py", "find": "return a + b", "replace": "return a - b"},
    }) + "\n")
    instances = tmp_path / "instances.jsonl"
    rows = generate_swe_mutations(repo, recipes, instances)
    assert "return a - b" in rows[0]["bug_patch"]
    assert "return a + b" in rows[0]["patch"]
    tasks = SWEBenchFamily().package_for_harbor(instances, tmp_path / "tasks", source_ref="local://mutation", dataset_version="1")
    task = tasks[0]
    assert f"git checkout {base_commit}" in (task / "environment/Dockerfile").read_text()
    assert "tests/test_calc.py::test_add" in (task / "tests/verifier.py").read_text()

    (repo / "calc.py").write_text("dirty\n")
    with pytest.raises(ValueError, match="must be clean"):
        generate_swe_mutations(repo, recipes, tmp_path / "dirty.jsonl")


def test_production_recipe_schemas_are_well_formed() -> None:
    schemas = Path(__file__).parents[1] / "schemas"
    for name in (
        "terminal-recipe.schema.json",
        "swe-mutation-recipe.schema.json",
        "nl2repo-production.schema.json",
    ):
        value = json.loads((schemas / name).read_text())
        assert value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert value["type"] == "object"
        assert value["required"]
