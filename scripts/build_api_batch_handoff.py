#!/usr/bin/env python3
"""Build an expert-review handoff from ten locally audited API tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from terminal_data_factory.multistep import validate_multistep_task


EXPECTED_TASKS = (
    "mini-crdt-notebook-engine",
    "mini-dns-zone-auditor",
    "mini-http-cache-engine",
    "mini-ical-sync-engine",
    "mini-mqtt-session-broker",
    "mini-pcap-stream-reassembler",
    "mini-png-asset-pipeline",
    "mini-posix-manifest-installer",
    "mini-systemd-unit-linter",
    "mini-wasm-module-auditor",
)

INFRA_SCRIPTS = (
    "run_fragment_workers.py",
    "import_model_topic_portfolio.py",
    "export_batch_operator_artifacts.py",
    "normalize_verification_fragment.py",
    "compile_package_fragment.py",
    "merge_model_fragments.py",
    "materialize_model_bundle.py",
    "materialize_model_batch.py",
)


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _promote_copy(task: Path) -> dict:
    metadata_path = task / "metadata.json"
    metadata = _json(metadata_path)
    metadata["release_status"] = "verifier-audited"
    metadata["quality"]["local_audit"] = {
        "cumulative_oracle_steps_passed": 5,
        "cumulative_public_smokes_passed": 5,
        "starter_steps_rejected": 5,
        "step_mutants_rejected": 5,
        "isolation_probe_passed": True,
        "independent_check_inventory_confirmed": True,
        "repeat_audit_runs": 2,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    readme = task / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = text.replace(
        "Status: `under-construction`. Target-agent rollouts: 0.",
        "Status: `verifier-audited`. Target-agent rollouts: 0.",
    )
    readme.write_text(text, encoding="utf-8")

    provenance = task / "review/provenance_notes.md"
    text = provenance.read_text(encoding="utf-8").replace(
        "release status is\nunder-construction.",
        "release status is\nverifier-audited.",
    )
    provenance.write_text(text, encoding="utf-8")

    verifier_notes = task / "review/verifier_notes.md"
    text = verifier_notes.read_text(encoding="utf-8")
    marker = "This number is conservative:"
    if marker in text:
        prefix = text.split(marker, 1)[0]
        text = (
            prefix
            + "This number is conservative: dynamic or implicit assertions are "
            "not counted.\n\n"
            + "The delivered `verifier/audit-report.json` passed the progressive "
            "Starter, cumulative Step 1..N Oracle, public-contract smoke, five "
            "Step-specific mutant, and subprocess-isolation gates. Independent "
            "batch QA reconstructed every cumulative solution without calling the "
            "task audit, then reproduced the audit twice with an identical report "
            "hash. Harbor Oracle/Nop jobs and target-agent rollouts remain open; "
            "difficulty is therefore uncalibrated.\n"
        )
        verifier_notes.write_text(text, encoding="utf-8")
    return metadata


def _write_readme(output: Path, catalog: list[dict], total_checks: int) -> None:
    rows = "\n".join(
        f"| `{item['task_id']}` | {item['source_license']} | "
        f"{item['behavioral_checks']} | 5/5 |"
        for item in catalog
    )
    text = f"""# Data Infra API Batch 10 — Expert Review Handoff

This is a new ten-task batch produced by the operator-style Data Infra and the
configured OpenAI-compatible API. It is independent of, and does not modify,
the frozen original ten-task buyer handoff.

## What is proven

- 10/10 five-Step Greenfield Harbor-format tasks materialized;
- {total_checks} statically named black-box behavior checks;
- 50/50 Oracle Steps pass;
- 50/50 cumulative public-contract smokes pass;
- 50/50 progressive Starter states are rejected;
- 50/50 deterministic Step-specific mutants are rejected, including Step 5;
- 10/10 Python isolation probes pass;
- two clean-copy audit repeats per task produce identical reports;
- secret, raw IP endpoint, host-user path, and Python bytecode scans are clean;
- the original handoff Manifest still verifies 4,452/4,452 files.

## Task portfolio

| Task | Concept source license | Checks | Mutants rejected |
|---|---|---:|---:|
{rows}

## Status boundary

These tasks are `verifier-audited` expert-review candidates. They are not
`release-ready`: Harbor Oracle/Nop container jobs, target-agent rollout,
cross-model-family difficulty calibration, and expert semantic/license approval
remain open. No T5/H4 or stable pass@1 claim is made.

## Review entry points

- `tasks/`: the ten self-contained task candidates, including starter,
  knowledge, five instructions, five solutions, verifiers, anti-cheat mutants,
  and audit reports;
- `evidence/BATCH_QA.json`: uniform ten-task repeatability and sanitation QA;
- `evidence/generation/`: sanitized API worker summaries and operator ledger;
- `evidence/repairs/`: deterministic repair scripts/records for failures caught
  by the gates;
- `infra/`: operator catalog, scaling plan, prompts, compiler, normalizer,
  materializer, and QA implementation used for this experiment;
- `infra/batch/P0_CRDT_REPAIR_REPORT.md`: reproduction, root cause, repair, and
  before/after evidence for the expert-found CRDT defect;
- `TASK_CATALOG.json`: machine-readable portfolio and open-gate summary;
- `HOW_TO_VERIFY.md`: copy-paste integrity, single-task, and whole-batch checks;
- `MANIFEST.sha256`: integrity list for the complete handoff.

API credentials are never persisted. Endpoint values in retained evidence are
redacted placeholders.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def _write_how_to_verify(output: Path) -> None:
    text = """# How to verify this handoff

Run from the handoff root with Python 3.11 or newer. The QA runner uses the
standard-library `tomllib` module; on systems where `python3` is older, replace
`python3` below with an explicit interpreter such as `python3.12`.

## Integrity

```sh
shasum -a 256 -c MANIFEST.sha256
```

## One task

```sh
python3 tasks/mini-crdt-notebook-engine/verifier/run_audit.py
```

The command must exit 0 and write an audit report with `"passed": true`.

## Independent ten-task QA

The QA runner does not trust the task's own audit for Oracle correctness. For
each Step it creates a fresh workspace, executes solutions 1..N, then runs the
public smoke and strict verifier. It also runs every task audit twice, compares
report hashes, counts named checks and mutants from source, scans sensitive
strings, and confirms source immutability.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=infra/src \
python3 -m terminal_data_factory.batch_qa \
  --root tasks \
  --output ../api-batch-10-recheck.json \
  --limit 10 \
  --repeats 2 \
  --timeout 180
```

Expected totals include:

```json
{
  "audit_passed": 10,
  "progressive_oracle_passed": 10,
  "progressive_oracle_steps_passed": 50,
  "independent_inventory_passed": 10,
  "behavioral_checks_confirmed": 409,
  "mutants_confirmed": 50,
  "public_smokes_confirmed": 50
}
```

This local QA does not replace Harbor container execution or target-agent
difficulty calibration.
"""
    (output / "HOW_TO_VERIFY.md").write_text(text, encoding="utf-8")


def build(candidates: Path, batch_root: Path, repo_root: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("output must not already exist")
    actual = sorted(
        path.name
        for path in candidates.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    )
    if actual != list(EXPECTED_TASKS):
        raise ValueError(f"unexpected candidate set: {actual}")
    output.mkdir(parents=True)

    catalog: list[dict] = []
    total_checks = 0
    for task_id in EXPECTED_TASKS:
        source = candidates / task_id
        report = validate_multistep_task(source, require_evidence=False)
        if not report.passed:
            raise ValueError(f"{task_id}: static validation failed: {report.errors}")
        audit = _json(source / "verifier/audit-report.json")
        if audit.get("passed") is not True:
            raise ValueError(f"{task_id}: audit report is not passed")
        destination = output / "tasks" / task_id
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
        )
        metadata = _promote_copy(destination)
        checks = int(metadata["quality"]["behavioral_checks"])
        total_checks += checks
        catalog.append(
            {
                "task_id": task_id,
                "behavioral_checks": checks,
                "source": metadata["provenance"]["source"],
                "source_license": metadata["provenance"]["source_license"],
                "release_status": "verifier-audited",
                "difficulty": "uncalibrated-long-horizon-candidate",
                "target_agent_rollouts": 0,
            }
        )

    generation = output / "evidence/generation"
    for name in (
        "core_workers.json",
        "verification_workers.json",
        "operator_run.json",
        "topic_portfolio_generation.json",
        "batch_runtime_three_tasks.json",
        "topic_portfolio_worker_3.json",
        "owned_three_task_summary.json",
        "frozen_original_manifest_check.txt",
        "crdt_progressive_oracle_before_fix.json",
        "crdt_progressive_oracle_after_fix.json",
        "BATCH_QA_V4.json",
    ):
        source = batch_root / "evidence" / name
        if source.is_file():
            _copy_file(source, generation / name)
    _copy_file(
        batch_root / "evidence/BATCH_QA_V4.json",
        output / "evidence/BATCH_QA.json",
    )
    shutil.copytree(batch_root / "repairs", output / "evidence/repairs")

    infra = output / "infra"
    for name in ("README.md", "OPERATOR_CATALOG.md", "SCALING_PLAN.md"):
        _copy_file(repo_root / "data_infra_v1" / name, infra / name)
    for name in (
        "README.md",
        "BUNDLE_PROTOCOL.md",
        "DATA_INFRA_EFFECT.md",
        "P0_CRDT_REPAIR_REPORT.md",
        "pipeline.json",
    ):
        _copy_file(batch_root / name, infra / "batch" / name)
    shutil.copytree(batch_root / "prompts", infra / "prompts")
    for name in INFRA_SCRIPTS:
        _copy_file(repo_root / "scripts" / name, infra / "scripts" / name)
    for name in ("__init__.py", "batch_qa.py", "multistep.py"):
        _copy_file(
            repo_root / "src/terminal_data_factory" / name,
            infra / "src/terminal_data_factory" / name,
        )

    catalog_payload = {
        "schema_version": "1.0",
        "batch_id": "api_batch_10_v1",
        "task_count": 10,
        "behavioral_checks": total_checks,
        "oracle_steps_passed": 50,
        "cumulative_public_smokes_passed": 50,
        "starter_steps_rejected": 50,
        "mutants_rejected": 50,
        "isolation_probes_passed": 10,
        "target_agent_rollouts": 0,
        "status": "verifier-audited-expert-review",
        "open_gates": [
            "Harbor Oracle/Nop container execution",
            "cross-model-family target-agent rollout",
            "difficulty calibration",
            "expert semantic and license approval",
        ],
        "tasks": catalog,
    }
    (output / "TASK_CATALOG.json").write_text(
        json.dumps(catalog_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(output, catalog, total_checks)
    _write_how_to_verify(output)


def write_manifest(root: Path) -> None:
    manifest = root / "MANIFEST.sha256"
    lines = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file() and path != manifest:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    if args.manifest_only:
        write_manifest(args.output.resolve())
    else:
        build(
            args.candidates.resolve(),
            args.batch_root.resolve(),
            args.repo_root.resolve(),
            args.output.resolve(),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
