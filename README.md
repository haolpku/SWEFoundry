# SWEFoundry

Unified infrastructure for producing verifiable coding tasks, Harbor rollouts,
rewards, and training trajectories.

The factory separates topic discovery, portfolio selection, task design,
contract compilation, code/verifier synthesis, mutant planning, independent
QA, Harbor execution planning, rollout calibration, and release packaging.
Static quality and calibrated difficulty are deliberately separate gates.

## Data lifecycle

SWEFoundry treats task correctness, model difficulty, and trajectory quality as
separate gates:

```text
source → construct → materialize → independent QA → difficulty calibration
       → Harbor rollout → reward recovery/filtering → Hugging Face shards
```

The control plane is built around three records:

- `TaskRecord`: immutable task identity, instruction, workspace materializer,
  environment, verifier, provenance, version, content hash, and lineage;
- `TrajectoryRecord`: one model/agent attempt, its exact task hash, ATIF URI,
  token/cost/time metrics, and runtime configuration;
- `RewardRecord`: the score and component metrics for one trajectory, including
  whether it was online, recovered from delayed artifacts, partial, or rejected.

One task can have many trajectories. Reward records may be recomputed without
changing the original task or trajectory.

Machine-readable JSON Schemas are published under `schemas/`. The Python
dataclasses additionally recompute and verify task content hashes at load time.

## Quality and scale control plane

The v0.2 control-plane modules live in `src/terminal_data_factory/`:

| Capability | Module | What it prevents |
| --- | --- | --- |
| Common records | `records.py` | Incompatible per-benchmark metadata |
| Version/hash/lineage | `records.py`, `lineage.py` | Silent task drift, duplicates, and train/test leakage |
| Independent task QA | `batch_qa.py`, `audit.py` | Trusting a task's self-reported audit |
| Mutant generation | `mutants.py` | Weak verifiers that accept plausible wrong solutions |
| Difficulty calibration | `calibration.py` | Scaling thousands of trivial or broken tasks |
| Delayed-reward recovery | `recovery.py` | Dropping valid Harbor trajectories after artifact races |
| HF shard export | `hf_export.py` | Millions of tiny files and non-reproducible releases |

### Record validation and deduplication

`task_hash` covers the visible instruction, workspace identity, environment,
and verifier. A trajectory or reward must reference the same task ID, version,
and hash. The validator also reports exact content duplicates and normalized
query duplicates.

```sh
swef records-validate \
  --tasks records/tasks.jsonl \
  --trajectories records/trajectories.jsonl \
  --rewards records/rewards.jsonl
```

### Recipe-driven mutants

Mutation recipes apply one bounded replacement each. Generated mutants are
content-addressed and written with a manifest. Compilation, partial-test, and
mutation-score gates remain the responsibility of independent QA; malformed
or non-running mutants must not inflate verifier quality.

```json
{
  "rules": [
    {
      "name": "ignore-duplicate-id",
      "path": "solution/files/ledger.py",
      "find": "raise ValueError(\"duplicate id\")",
      "replace": "continue"
    }
  ]
}
```

```sh
swef mutants-generate --task-root TASK --rules mutation-rules.json --output MUTANTS
```

### Difficulty calibration

Calibration consumes repeated rewards and trajectory-to-model mappings. It
reports full-pass rate, mean partial reward, per-model pass rates, and one of
`trivial`, `easy`, `medium`, `hard`, or `frontier_or_broken`. The final label
must be based on multiple model families and seeds; Oracle success alone is not
a difficulty measurement.

```sh
swef calibrate \
  --trajectories records/trajectories.jsonl \
  --rewards records/rewards.jsonl \
  --output reports/difficulty.json
```

### Strict recovered rescore

Harbor or shared storage can expose a completed `reward.txt`/`reward.json`
after the initial result was marked `RewardFileNotFoundError`. Recovery is
allowed only when the original exception is allowlisted, both reward files are
present and agree, the score is valid, and no compliance or anti-hack failure
is present. The original result is never overwritten; a new RewardRecord keeps
its hash and recovery reason.

```sh
swef recover-reward \
  --trial HARBOR_TRIAL_DIR \
  --task-id TASK_ID --task-version 1.0.0 --task-hash sha256:... \
  --output records/recovered-reward.jsonl
```

### Hugging Face shards

The streaming standard-library exporter currently emits deterministic JSONL
shards, SHA-256 checksums, and a release manifest without retaining the full
dataset in memory. Parquet is a planned optional backend; compressed task
artifacts and full ATIF files should be uploaded separately and referenced by
URI and checksum from the records.

```sh
swef hf-export \
  --input records/trajectories.jsonl \
  --output-dir release/trajectories \
  --prefix train --shard-size 500
```

## Storage boundary

GitHub contains only infrastructure code, schemas, recipes, manifests, tests,
and tiny smoke fixtures. It must not contain production tasks, reference
solutions, hidden tests, raw trajectories, or full QA logs.

| Content | Storage |
| --- | --- |
| Code, schemas, recipes, tiny smoke fixtures | GitHub |
| Released task/record shards | Hugging Face Datasets |
| Hidden verifiers and restricted solutions | Private Hugging Face/VEPFS |
| Raw workspaces, Docker cache, rollout logs | VEPFS/object storage |
| Full ATIF trajectories and compressed artifacts | Hugging Face/VEPFS |

The public smoke fixtures below intentionally include their solutions and are
not contamination-resistant benchmark data.

## Cross-family smoke batch

[`examples/family-smoke-v1`](examples/family-smoke-v1) adds three compact,
deterministic tasks that exercise `synthetic-repair`, `nl2repo-lite`, and
`repo-reproduction` semantics through the same Harbor-shaped task contract.
Their independent audit requires the Starter to fail, the Oracle to pass every
behavioral check, and repeated Oracle rewards to be byte-for-byte stable.

```sh
python scripts/validate_family_smoke.py
```

## Current verified example

[`examples/api-batch-10-v1`](examples/api-batch-10-v1) contains the second,
API-generated ten-task experiment:

- 10 five-Step tasks;
- 409 independently counted behavioral checks;
- 50/50 cumulative Oracle Steps;
- 50/50 public-contract smokes;
- 50/50 Step-specific mutants rejected;
- 10/10 deterministic repeated audits;
- 10/10 clean secret, endpoint, user-path, and bytecode scans.

The example is `verifier-audited` and ready for expert review. It is not
`release-ready`: Harbor Oracle/Nop execution, cross-model-family target-agent
rollouts, stable pass@1 measurement, and expert semantic/license approval
remain open.

This repository does not contain or modify the previously frozen first
ten-task buyer handoff.

## Quick start

Python 3.11 or newer is required.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest
pytest -q
```

List and run the control-plane operators:

```sh
tdf operator-list
tdf pipeline-run \
  --spec data_infra/pipelines/topic_to_calibration.json \
  --work-dir /tmp/tdf-operator-run
```

`swef` is the preferred project CLI. The historical `tdf` executable remains
as a backward-compatible alias for existing automation.

Recheck the ten-task example:

```sh
cd examples/api-batch-10-v1
shasum -a 256 -c MANIFEST.sha256
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=infra/src \
  python3.12 -m terminal_data_factory.batch_qa \
  --root tasks \
  --output /tmp/api-batch-10-recheck.json \
  --limit 10 \
  --repeats 2 \
  --timeout 180
```

The independent QA runner does not trust a task's own `run_audit.py` for
Oracle correctness. For every Step it creates a fresh workspace, installs
solutions 1…N, runs the public smoke, runs the strict verifier, and separately
counts checks, smokes, and mutants from source. Failed named checks and their
bounded tracebacks are retained as repair evidence.

## QA-gated repair generations

Failed API generations are repaired through immutable, monotonic generations:

```sh
PYTHONPATH=src python scripts/run_task_repair_workers.py \
  --tasks-root candidates \
  --qa-report evidence/BATCH_QA.json \
  --output-root repairs \
  --prompt data_infra/prompts/task_repair.md \
  --summary evidence/REPAIR_WORKERS.json

PYTHONPATH=src python scripts/apply_task_repairs.py \
  --tasks-root candidates \
  --repairs-root repairs \
  --output-root candidates-repaired \
  --evidence evidence/APPLY.json

PYTHONPATH=src python scripts/promote_task_repairs.py \
  --before-root candidates \
  --after-root candidates-repaired \
  --before-qa evidence/BATCH_QA.json \
  --after-qa evidence/BATCH_QA_REPAIRED.json \
  --output-root candidates-next \
  --evidence evidence/PROMOTE.json
```

The worker accepts only bounded complete-file replacements under
`environment/`, `steps/`, and `verifier/`. It cannot replace task metadata or
generated audit reports. Promotion happens per task only when the independent
QA score strictly improves; regressions and no-op repairs retain the prior
generation. The score includes full release gates, Step pass count, and
aggregate per-check correctness so partial but real progress is not discarded.

## Repository layout

- `src/terminal_data_factory/`: operator runtime, built-in operators,
  common records, lineage, mutation, calibration, reward recovery, shard
  export, multi-step validation, and independent batch QA;
- `data_infra/`: operator catalog, pipeline DAG, inputs, and scale-out plan;
- `scripts/`: deterministic API-worker, compiler, normalizer, materializer,
  repair, monotonic-promotion, and handoff builders;
- `tests/`: unit and regression tests, including the progressive-Oracle
  false-positive regression;
- `examples/api-batch-10-v1/`: self-contained expert-review handoff and
  machine-readable evidence;
- `examples/family-smoke-v1/`: three tiny cross-family regression fixtures;
- `docs/`: sandbox, open-source reference, and 1,000/10,000-task scaling notes.

## Credentials and model APIs

Model credentials must be supplied only through process environment variables.
Do not commit keys or raw private endpoints. Retained worker evidence stores
redacted endpoint placeholders and `credentials_persisted=false`.

## Quality boundary

Oracle success proves executability, Starter failure proves the task is not
already solved, and mutant rejection probes verifier sensitivity. None of
those measurements establishes model difficulty. Difficulty labels require
repeated, controlled rollouts across independent model families and human
review of successful and failed trajectories.
