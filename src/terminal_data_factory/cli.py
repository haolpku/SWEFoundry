from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator

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
from .calibration import calibrate
from .hf_export import export_jsonl_shards
from .families import builtin_families, get_family
from .families.base import write_jsonl
from .lineage import exact_duplicate_groups, load_task_records, query_duplicate_groups, validate_lineage
from .mutants import generate_mutants, load_rules
from .records import RewardRecord, TrajectoryRecord
from .recovery import recover_trial


def _read_jsonl(path: Path) -> list[dict]:
    return list(_iter_jsonl(path))


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


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
    parser = argparse.ArgumentParser(prog=Path(sys.argv[0]).name)
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
    records = sub.add_parser("records-validate")
    records.add_argument("--tasks", type=Path, required=True)
    records.add_argument("--trajectories", type=Path)
    records.add_argument("--rewards", type=Path)
    mutants = sub.add_parser("mutants-generate")
    mutants.add_argument("--task-root", type=Path, required=True)
    mutants.add_argument("--rules", type=Path, required=True)
    mutants.add_argument("--output", type=Path, required=True)
    calibration = sub.add_parser("calibrate")
    calibration.add_argument("--trajectories", type=Path, required=True)
    calibration.add_argument("--rewards", type=Path, required=True)
    calibration.add_argument("--output", type=Path, required=True)
    recovery = sub.add_parser("recover-reward")
    recovery.add_argument("--trial", type=Path, required=True)
    recovery.add_argument("--task-id", required=True)
    recovery.add_argument("--task-version", required=True)
    recovery.add_argument("--task-hash", required=True)
    recovery.add_argument("--output", type=Path, required=True)
    export = sub.add_parser("hf-export")
    export.add_argument("--input", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    export.add_argument("--prefix", required=True)
    export.add_argument("--shard-size", type=int, default=500)
    sub.add_parser("family-list")
    family_import = sub.add_parser("family-import")
    family_import.add_argument("--family", required=True)
    family_import.add_argument("--source", type=Path, required=True)
    family_import.add_argument("--source-ref", required=True)
    family_import.add_argument("--dataset-version", required=True)
    family_import.add_argument("--output", type=Path, required=True)
    family_validate = sub.add_parser("family-validate")
    family_validate.add_argument("--tasks", type=Path, required=True)
    family_package = sub.add_parser("family-package")
    family_package.add_argument("--family", required=True)
    family_package.add_argument("--source", type=Path, required=True)
    family_package.add_argument("--source-ref", required=True)
    family_package.add_argument("--dataset-version", required=True)
    family_package.add_argument("--output", type=Path, required=True)
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
    if args.command == "records-validate":
        tasks = load_task_records(args.tasks)
        errors = validate_lineage(tasks)
        task_keys = {(item.task_id, item.task_version, item.task_hash) for item in tasks}
        trajectories = [TrajectoryRecord.from_dict(item) for item in _read_jsonl(args.trajectories)] if args.trajectories else []
        trajectory_ids = {item.trajectory_id for item in trajectories}
        for item in trajectories:
            if (item.task_id, item.task_version, item.task_hash) not in task_keys:
                errors.append(f"{item.trajectory_id}: unknown task identity")
        rewards = [RewardRecord.from_dict(item) for item in _read_jsonl(args.rewards)] if args.rewards else []
        for item in rewards:
            if item.trajectory_id not in trajectory_ids:
                errors.append(f"{item.trajectory_id}: reward has no trajectory")
            if (item.task_id, item.task_version, item.task_hash) not in task_keys:
                errors.append(f"{item.trajectory_id}: reward has unknown task identity")
        summary = {
            "passed": not errors,
            "tasks": len(tasks),
            "trajectories": len(trajectories),
            "rewards": len(rewards),
            "exact_duplicates": exact_duplicate_groups(tasks),
            "query_duplicates": query_duplicate_groups(tasks),
            "errors": errors,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if not errors else 1
    if args.command == "mutants-generate":
        artifacts = generate_mutants(args.task_root.resolve(), load_rules(args.rules), args.output.resolve())
        print(json.dumps({"generated": len(artifacts), "output": str(args.output)}, indent=2))
        return 0
    if args.command == "calibrate":
        trajectories = [TrajectoryRecord.from_dict(item) for item in _read_jsonl(args.trajectories)]
        rewards = [RewardRecord.from_dict(item) for item in _read_jsonl(args.rewards)]
        models = {item.trajectory_id: item.model for item in trajectories}
        report = {"schema_version": "difficulty-v1", "tasks": [item.as_dict() for item in calibrate(rewards, models)]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if args.command == "recover-reward":
        record = recover_trial(args.trial.resolve(), task_id=args.task_id, task_version=args.task_version, task_hash=args.task_hash)
        if record is None:
            print("No strictly recoverable reward found")
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record.as_dict(), sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(record.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "hf-export":
        manifest = export_jsonl_shards(_iter_jsonl(args.input), args.output_dir.resolve(), prefix=args.prefix, shard_size=args.shard_size)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    if args.command == "family-list":
        for family_id, family in sorted(builtin_families().items()):
            print(json.dumps(family.descriptor.as_dict(), sort_keys=True))
        return 0
    if args.command == "family-import":
        family = get_family(args.family)
        records = family.import_records(
            args.source.resolve(),
            source_ref=args.source_ref,
            dataset_version=args.dataset_version,
        )
        count = write_jsonl(records, args.output.resolve())
        print(json.dumps({"family": args.family, "imported": count, "output": str(args.output)}, indent=2))
        return 0
    if args.command == "family-validate":
        records = load_task_records(args.tasks)
        errors = []
        for record in records:
            try:
                family = get_family(record.family)
            except ValueError as exc:
                errors.append(f"{record.task_id}: {exc}")
                continue
            errors.extend(family.validate_record(record))
        report = {"passed": not errors, "records": len(records), "errors": errors}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not errors else 1
    if args.command == "family-package":
        family = get_family(args.family)
        destinations = family.package_for_harbor(
            args.source.resolve(),
            args.output.resolve(),
            source_ref=args.source_ref,
            dataset_version=args.dataset_version,
        )
        print(json.dumps({"family": args.family, "packaged": len(destinations), "tasks": [str(path) for path in destinations]}, indent=2))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
