# Code Data Infra

Operator-style infrastructure for producing and auditing multi-step,
Greenfield Terminal-Bench candidates.

The factory separates topic discovery, portfolio selection, task design,
contract compilation, code/verifier synthesis, mutant planning, independent
QA, Harbor execution planning, rollout calibration, and release packaging.
Static quality and calibrated difficulty are deliberately separate gates.

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
tdf operator-run \
  --pipeline data_infra/pipelines/topic_to_calibration.json \
  --work-dir /tmp/tdf-operator-run
```

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
  multi-step validator, and independent batch QA;
- `data_infra/`: operator catalog, pipeline DAG, inputs, and scale-out plan;
- `scripts/`: deterministic API-worker, compiler, normalizer, materializer,
  repair, monotonic-promotion, and handoff builders;
- `tests/`: unit and regression tests, including the progressive-Oracle
  false-positive regression;
- `examples/api-batch-10-v1/`: self-contained expert-review handoff and
  machine-readable evidence;
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
