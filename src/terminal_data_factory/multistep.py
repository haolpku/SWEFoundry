from __future__ import annotations

import json
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


SECRET = re.compile(r"sk-[A-Za-z0-9]{20,}")
REWARD_KEYS = {
    "correctness",
    "code_quality",
    "reasoning",
    "efficiency",
    "weighted_total",
    "release_pass",
}


@dataclass
class MultiStepReport:
    task_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def load_multistep_catalog(root: Path) -> dict:
    return json.loads((root / "multistep_v1/catalog.json").read_text())


def discover_multistep_tasks(root: Path) -> list[Path]:
    tasks = root / "multistep_v1/tasks"
    if not tasks.is_dir():
        return []
    return sorted(path for path in tasks.iterdir() if (path / "task.toml").is_file())


def _harbor_trial_result(job: Path) -> dict | None:
    trials = [
        path / "result.json"
        for path in job.iterdir()
        if path.is_dir() and (path / "result.json").is_file()
    ]
    if len(trials) != 1:
        return None
    return json.loads(trials[0].read_text())


def validate_multistep_task(task: Path, require_evidence: bool = True) -> MultiStepReport:
    report = MultiStepReport(task.name)
    required = [
        "README.md",
        "metadata.json",
        "task.toml",
        "environment/Dockerfile",
        "environment/knowledge/index.md",
        "environment/knowledge/public_api.md",
        "environment/knowledge/public_api.json",
        "environment/codebase/public_contract_tests/README.md",
        "rubrics",
        "steps",
        "verifier/anti_cheat",
        "verifier/run_audit.py",
    ]
    for relative in required:
        if not (task / relative).exists():
            report.errors.append(f"missing {relative}")
    if report.errors:
        return report

    try:
        config = tomllib.loads((task / "task.toml").read_text())
    except tomllib.TOMLDecodeError as exc:
        report.errors.append(f"invalid task.toml: {exc}")
        return report
    if config.get("schema_version") != "1.3":
        report.errors.append("Harbor schema_version must be 1.3")
    if config.get("multi_step_reward_strategy") != "final":
        report.errors.append("multi_step_reward_strategy must be final")
    if config.get("artifacts") != ["/app/workspace"]:
        report.errors.append("artifacts must be ['/app/workspace']")
    if config.get("environment", {}).get("allow_internet") is not False:
        report.errors.append("environment.allow_internet must be false")
    authors = config.get("task", {}).get("authors", [])
    if not authors or not authors[0].get("name"):
        report.errors.append("task authors are missing")

    declared_steps = [item.get("name") for item in config.get("steps", [])]
    actual_steps = sorted(
        path.name for path in (task / "steps").iterdir() if path.is_dir()
    )
    if len(declared_steps) != 5 or len(set(declared_steps)) != 5:
        report.errors.append("task must declare exactly five unique steps")
    if declared_steps != actual_steps:
        report.errors.append("declared step order/directories differ")
    total_tests = 0
    public_contract = json.loads(
        (task / "environment/knowledge/public_api.json").read_text()
    )
    contract_steps = public_contract.get("steps", [])
    if [item.get("number") for item in contract_steps] != [1, 2, 3, 4, 5]:
        report.errors.append("public API contract must cover Steps 1-5")
    if any(len(item.get("public_cases", [])) < 2 for item in contract_steps):
        report.errors.append(
            "each public API contract Step needs at least two behavior cases"
        )
    if not public_contract.get("policy", {}).get(
        "hidden_tests_must_not_require_undisclosed_public_names"
    ):
        report.errors.append("public API disclosure policy is missing")
    public_tests = sorted(
        (task / "environment/codebase/public_contract_tests").glob(
            "step_*_smoke.py"
        )
    )
    if len(public_tests) != 5:
        report.errors.append("exactly five public contract tests are required")

    # Workers may keep the black-box runner and reward policy in a shared
    # verifier module while each Step has only a small, explicit wrapper.  Audit
    # the local verifier support as a unit instead of requiring duplicated
    # security-critical code in all five wrappers.
    verifier_modules = {
        path.stem: path.read_text()
        for path in sorted((task / "verifier").glob("*.py"))
        if path.is_file()
    }
    verifier_support = "\n".join(verifier_modules.values())

    for step_number, step_name in enumerate(declared_steps, 1):
        step = task / "steps" / step_name
        for relative in (
            "instruction.md",
            "solution/solve.sh",
            "tests/test.sh",
            "tests/verifier.py",
        ):
            if not (step / relative).is_file():
                report.errors.append(f"{step_name}: missing {relative}")
        if not (step / "solution/files").is_dir() or not any(
            (step / "solution/files").iterdir()
        ):
            report.errors.append(f"{step_name}: solution payload is empty")
        verifier = step / "tests/verifier.py"
        instruction = step / "instruction.md"
        if instruction.is_file():
            instruction_text = instruction.read_text()
            expected_smoke = (
                f"python public_contract_tests/step_{step_number:02d}_smoke.py"
            )
            if (
                "/app/knowledge/public_api.md" not in instruction_text
                or expected_smoke not in instruction_text
            ):
                report.errors.append(
                    f"{step_name}: public contract/smoke instructions missing"
                )
        if verifier.is_file():
            text = verifier.read_text()
            imported_local_module = any(
                re.search(
                    rf"(?m)^\s*(?:from\s+{re.escape(module)}\s+import|"
                    rf"import\s+{re.escape(module)}(?:\s|$))",
                    text,
                )
                for module in verifier_modules
            )
            uses_shared_verifier = (
                "from verifier." in text
                or "import verifier." in text
                or imported_local_module
            )
            policy_text = text + ("\n" + verifier_support if uses_shared_verifier else "")
            if (
                '"release_pass"' not in policy_text
                and "'release_pass'" not in policy_text
            ) or "correctness == 1.0" not in policy_text:
                report.errors.append(f"{step_name}: strict correctness gate missing")
            if '"-I"' not in policy_text and "'-I'" not in policy_text:
                report.errors.append(f"{step_name}: candidate subprocess is not isolated")
            match = re.search(r"summary.*?tests", text, re.DOTALL)
            if match:
                total_tests += 1
        shell = step / "tests/test.sh"
        if shell.is_file():
            text = shell.read_text()
            if "env -u PYTHONPATH -u PYTHONHOME" not in text or ' -I ' not in text:
                report.errors.append(f"{step_name}: verifier process isolation missing")
    metadata = json.loads((task / "metadata.json").read_text())
    behavioral = metadata.get("quality", {}).get("behavioral_checks", 0)
    if behavioral < 30:
        report.errors.append("fewer than 30 declared behavioral checks")
    if metadata.get("steps") != 5:
        report.errors.append("metadata must declare five steps")
    if metadata.get("release_status") not in {
        "under-construction",
        "verifier-audited",
        "rollout-calibrated",
    }:
        report.errors.append("invalid release status")
    if metadata.get("quality", {}).get("curated_false_positives", 0) < 5:
        report.errors.append("metadata declares fewer than five curated false positives")

    knowledge_bytes = sum(
        path.stat().st_size
        for path in (task / "environment/knowledge").rglob("*")
        if path.is_file()
    )
    if knowledge_bytes < 1500:
        report.errors.append("knowledge corpus is too small")
    mutants = sorted((task / "verifier/anti_cheat").glob("fp*"))
    if len(mutants) < 5:
        report.errors.append("fewer than five curated false positives")

    for path in task.rglob("*"):
        if not path.is_file() or "harbor_jobs" in path.parts:
            continue
        if path.name in {".DS_Store"} or path.suffix in {".pyc", ".pyo"}:
            report.errors.append(f"generated residue: {path.relative_to(task)}")
            continue
        if path.stat().st_size <= 2_000_000:
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            if SECRET.search(text):
                report.errors.append(f"secret-like token: {path.relative_to(task)}")

    if require_evidence:
        audit = task / "verifier/audit-report.json"
        audit_report = json.loads(audit.read_text()) if audit.is_file() else {}
        if not audit_report.get("passed"):
            report.errors.append("passing audit-report.json is missing")
        else:
            audit_checks = sum(
                step["oracle"]["summary"]["tests"]
                for step in audit_report.get("steps", [])
            )
            if audit_checks != behavioral:
                report.errors.append("metadata behavioral check count differs from audit")
            audited_mutants = audit_report.get("mutants", [])
            mutant_steps = {
                int(item["step"].split("-", 1)[0])
                for item in audited_mutants
                if item.get("rejected") and isinstance(item.get("step"), str)
            }
            if len(audited_mutants) < 5 or mutant_steps != {1, 2, 3, 4, 5}:
                report.errors.append("audit must reject at least one mutant for every step")
        for agent, expected in (("oracle", 1.0), ("nop", 0.0)):
            job = task / "harbor_jobs" / f"{task.name}-{agent}-v1"
            if not (job / "result.json").is_file():
                report.errors.append(f"Harbor {agent} job is missing")
                continue
            result = _harbor_trial_result(job)
            if result is None:
                report.errors.append(f"Harbor {agent} job must contain one trial")
                continue
            steps = result.get("step_results", [])
            if len(steps) != 5 or any(item.get("exception_info") for item in steps):
                report.errors.append(f"Harbor {agent} step_results are incomplete")
                continue
            for item in steps:
                rewards = item.get("verifier_result", {}).get("rewards", {})
                if set(rewards) != REWARD_KEYS:
                    report.errors.append(f"Harbor {agent} reward schema differs")
                if rewards.get("release_pass") != expected:
                    report.errors.append(f"Harbor {agent} release_pass differs")
    return report


def validate_multistep_release(root: Path, require_evidence: bool = True) -> list[str]:
    catalog = load_multistep_catalog(root)
    task_paths = discover_multistep_tasks(root)
    errors = []
    expected = [item["id"] for item in catalog["tasks"]]
    actual = [path.name for path in task_paths]
    if catalog.get("task_count") != 10 or len(expected) != 10 or len(set(expected)) != 10:
        errors.append("catalog must define ten unique tasks")
    if set(actual) != set(expected):
        errors.append(
            f"catalog/task directories differ; missing={sorted(set(expected)-set(actual))}, "
            f"extra={sorted(set(actual)-set(expected))}"
        )
    domains = Counter(item["domain"] for item in catalog["tasks"])
    if len(domains) < 8:
        errors.append("release must span at least eight domains")
    reports = [
        validate_multistep_task(path, require_evidence=require_evidence)
        for path in task_paths
    ]
    for report in reports:
        errors.extend(f"{report.task_id}: {error}" for error in report.errors)
    return errors
