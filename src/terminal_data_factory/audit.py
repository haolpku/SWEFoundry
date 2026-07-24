from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import AuditResult, TaskFamily


PASS_THRESHOLD = 0.90


def _tree_digest(root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        hasher.update(path.relative_to(root).as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _run(command: list[str], *, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def _score(task_root: Path, workspace: Path, evidence: Path, result_dir: Path) -> tuple[float | None, str | None]:
    result_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "TDF_WORKSPACE": str(workspace),
        "TDF_EVIDENCE": str(evidence),
        "TDF_TESTS_DIR": str(task_root / "tests"),
        "TDF_REWARD_DIR": str(result_dir),
    })
    proc = _run(["bash", str(task_root / "tests/test.sh")], env=env)
    if proc.returncode not in (0, 1):
        return None, f"verifier crashed: {proc.stderr[-500:]}"
    try:
        return float((result_dir / "reward.txt").read_text(encoding="utf-8").strip()), None
    except (OSError, ValueError, KeyError) as exc:
        details = (proc.stderr or proc.stdout)[-500:]
        return None, f"invalid reward.txt: {exc}; verifier output: {details}"


def audit_task(task_root: Path) -> AuditResult:
    task = TaskFamily.load(task_root)
    errors: list[str] = []
    anti_scores: dict[str, float] = {}
    unsolved_score: float | None = None
    oracle_score: float | None = None
    reproducible: bool | None = None
    seed_sensitive: bool | None = None
    published_evidence_matches: bool | None = None
    behavioral_tests: int | None = None

    with tempfile.TemporaryDirectory(prefix=f"tdf-{task.id}-") as tmp:
        tmp_root = Path(tmp)
        evidence = tmp_root / "evidence"
        evidence.mkdir()
        gen = _run([
            "python3", str(task_root / "generator/generate.py"),
            "--output", str(evidence), "--seed", "20260722",
        ])
        if gen.returncode != 0:
            errors.append(f"generator failed: {gen.stderr[-500:]}")
            return AuditResult(task.id, None, None, {}, False, tuple(errors))

        evidence_repeat = tmp_root / "evidence-repeat"
        evidence_repeat.mkdir()
        repeat = _run([
            "python3", str(task_root / "generator/generate.py"),
            "--output", str(evidence_repeat), "--seed", "20260722",
        ])
        evidence_other = tmp_root / "evidence-other-seed"
        evidence_other.mkdir()
        other = _run([
            "python3", str(task_root / "generator/generate.py"),
            "--output", str(evidence_other), "--seed", "20260723",
        ])
        if repeat.returncode != 0 or other.returncode != 0:
            errors.append("generator repeat/alternate-seed execution failed")
        else:
            evidence_digest = _tree_digest(evidence)
            reproducible = evidence_digest == _tree_digest(evidence_repeat)
            seed_sensitive = evidence_digest != _tree_digest(evidence_other)
            published_evidence_matches = evidence_digest == _tree_digest(task_root / "evidence")
            if not reproducible:
                errors.append("generator is not reproducible for the same seed")
            if not seed_sensitive:
                errors.append("generator ignores seed changes")
            if not published_evidence_matches:
                errors.append("published evidence does not match seed 20260722")

        unsolved = tmp_root / "unsolved"
        shutil.copytree(task_root / "workspace", unsolved)
        unsolved_score, err = _score(task_root, unsolved, evidence, tmp_root / "unsolved-result")
        if err:
            errors.append(err)
        elif unsolved_score is not None and unsolved_score >= PASS_THRESHOLD:
            errors.append(f"unsolved score too high: {unsolved_score}")

        oracle = tmp_root / "oracle"
        shutil.copytree(task_root / "workspace", oracle)
        solve_env = os.environ.copy()
        solve_env.update({
            "TDF_WORKSPACE": str(oracle),
            "TDF_SOLUTION_DIR": str(task_root / "solution"),
        })
        solve = _run(["bash", str(task_root / "solution/solve.sh")], env=solve_env)
        if solve.returncode != 0:
            errors.append(f"oracle failed: {solve.stderr[-500:]}")
        else:
            oracle_score, err = _score(task_root, oracle, evidence, tmp_root / "oracle-result")
            if err:
                errors.append(err)
            elif oracle_score is not None and oracle_score < PASS_THRESHOLD:
                errors.append(f"oracle score too low: {oracle_score}")
            else:
                try:
                    ctrf = json.loads((tmp_root / "oracle-result/ctrf.json").read_text(encoding="utf-8"))
                    behavioral_tests = int(ctrf["results"]["summary"]["tests"])
                    if behavioral_tests < task.raw["quality"]["minimum_behavioral_tests"]:
                        errors.append(f"too few executed behavioral tests: {behavioral_tests}")
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    errors.append(f"invalid CTRF summary: {exc}")

        for cheat in sorted((task_root / "anti_cheat").glob("*.py")):
            cheated = tmp_root / f"cheat-{cheat.stem}"
            shutil.copytree(task_root / "workspace", cheated)
            apply_cheat = _run([
                "python3", str(cheat),
                "--workspace", str(cheated),
                "--evidence", str(evidence),
            ])
            if apply_cheat.returncode != 0:
                errors.append(f"anti-cheat setup failed {cheat.name}: {apply_cheat.stderr[-500:]}")
                continue
            score, err = _score(task_root, cheated, evidence, tmp_root / f"result-{cheat.stem}")
            if err:
                errors.append(f"{cheat.name}: {err}")
                continue
            assert score is not None
            anti_scores[cheat.stem] = score
            if score >= PASS_THRESHOLD:
                errors.append(f"anti-cheat escaped {cheat.name}: {score}")

    return AuditResult(
        task.id,
        unsolved_score,
        oracle_score,
        anti_scores,
        not errors,
        tuple(errors),
        reproducible,
        seed_sensitive,
        published_evidence_matches,
        behavioral_tests,
    )
