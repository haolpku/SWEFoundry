from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_task
from .planning import create_plan
from .multistep import (
    discover_multistep_tasks,
    validate_multistep_release,
    validate_multistep_task,
)
from .validation import discover_tasks, validate_catalog, validate_task
from .operators import ArtifactStore, PipelineRuntime, builtin_registry
from .batch_qa import run_batch_qa, write_summary


def factory_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_catalog(root: Path) -> int:
    print((root / "catalog.json").read_text(encoding="utf-8"))
    return 0


def cmd_validate_all(root: Path) -> int:
    paths = discover_tasks(root)
    reports = [validate_task(path) for path in paths]
    catalog_errors = validate_catalog(root, reports)
    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        print(f"{status} {report.task_id}")
        for error in report.errors:
            print(f"  error: {error}")
        for warning in report.warnings:
            print(f"  warning: {warning}")
    for error in catalog_errors:
        print(f"FAIL catalog: {error}")
    return 0 if reports and all(report.passed for report in reports) and not catalog_errors else 1


def cmd_audit_all(root: Path, output: Path | None, promote: bool) -> int:
    results = []
    for task_root in discover_tasks(root):
        result = audit_task(task_root)
        results.append(result.as_dict())
        print(f"{'PASS' if result.passed else 'FAIL'} {result.task_id}")
        for error in result.errors:
            print(f"  {error}")
    payload = {"results": results, "passed": bool(results) and all(item["passed"] for item in results)}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if promote and payload["passed"]:
        by_id = {item["task_id"]: item for item in results}
        for task_root in discover_tasks(root):
            manifest_path = task_root / "task.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("status") in {"draft", "buildable", "oracle-passed"}:
                manifest["status"] = "verifier-audited"
                manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            evidence_path = task_root / "docs/local-audit.json"
            evidence_path.write_text(json.dumps(by_id[task_root.name], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if payload["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tdf")
    parser.add_argument("--root", type=Path, default=factory_root())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    sub.add_parser("validate-all")
    audit = sub.add_parser("audit-all")
    audit.add_argument("--output", type=Path)
    audit.add_argument("--promote", action="store_true", help="record successful local audit and advance status")
    plan = sub.add_parser("plan")
    plan.add_argument("--instances", type=int, required=True)
    plan.add_argument("--rollouts", type=int, default=10)
    plan.add_argument("--shard-size", type=int, default=500)
    plan.add_argument("--output", type=Path, required=True)
    multistep = sub.add_parser("multistep-validate")
    multistep.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="validate present tasks without requiring all ten or execution evidence",
    )
    sub.add_parser("operator-list")
    pipeline = sub.add_parser("pipeline-run")
    pipeline.add_argument("--spec", type=Path, required=True)
    pipeline.add_argument("--work-dir", type=Path, required=True)
    artifact = sub.add_parser("artifact-show")
    artifact.add_argument("--digest", required=True)
    artifact.add_argument("--work-dir", type=Path, required=True)
    batch_qa = sub.add_parser("batch-qa")
    batch_qa.add_argument("--input", type=Path, required=True)
    batch_qa.add_argument("--output", type=Path)
    batch_qa.add_argument("--limit", type=int, default=10)
    batch_qa.add_argument("--repeats", type=int, default=2)
    batch_qa.add_argument("--timeout", type=int, default=180)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    if args.command == "catalog":
        return cmd_catalog(root)
    if args.command == "validate-all":
        return cmd_validate_all(root)
    if args.command == "audit-all":
        return cmd_audit_all(root, args.output, args.promote)
    if args.command == "plan":
        summary = create_plan(root, args.instances, args.rollouts, args.shard_size, args.output.resolve())
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    if args.command == "multistep-validate":
        if args.allow_incomplete:
            reports = [
                validate_multistep_task(path, require_evidence=False)
                for path in discover_multistep_tasks(root)
            ]
            for report in reports:
                print(f"{'PASS' if report.passed else 'FAIL'} {report.task_id}")
                for error in report.errors:
                    print(f"  {error}")
            return 0 if reports and all(report.passed for report in reports) else 1
        errors = validate_multistep_release(root, require_evidence=True)
        for error in errors:
            print(f"FAIL {error}")
        if not errors:
            print("PASS ten-task multi-step release")
        return 0 if not errors else 1
    if args.command == "operator-list":
        for name, operator in sorted(builtin_registry().items()):
            print(
                json.dumps(
                    {
                        "name": name,
                        "version": operator.version,
                        "inputs": dict(operator.input_types),
                        "outputs": dict(operator.output_types),
                    },
                    sort_keys=True,
                )
            )
        return 0
    if args.command == "pipeline-run":
        runtime = PipelineRuntime(
            ArtifactStore(args.work_dir.resolve()),
            builtin_registry(),
        )
        summary = runtime.run(args.spec.resolve())
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    if args.command == "artifact-show":
        artifact = ArtifactStore(args.work_dir.resolve()).get(args.digest)
        print(json.dumps(artifact.envelope(), indent=2, sort_keys=True))
        return 0
    if args.command == "batch-qa":
        summary = run_batch_qa(
            args.input,
            limit=args.limit,
            repeats=args.repeats,
            timeout=args.timeout,
        )
        if args.output:
            write_summary(summary, args.output, args.input)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["passed"] else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
