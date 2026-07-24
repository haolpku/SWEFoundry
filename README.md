# Code Data Infra

Operator-style infrastructure for producing and auditing multi-step,
Greenfield Terminal-Bench candidates.

The factory separates topic discovery, portfolio selection, task design,
contract compilation, code/verifier synthesis, mutant planning, independent
QA, Harbor execution planning, rollout calibration, and release packaging.
Static quality and calibrated difficulty are deliberately separate gates.

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
counts checks, smokes, and mutants from source.

## Repository layout

- `src/terminal_data_factory/`: operator runtime, built-in operators,
  multi-step validator, and independent batch QA;
- `data_infra/`: operator catalog, pipeline DAG, inputs, and scale-out plan;
- `scripts/`: deterministic API-worker, compiler, normalizer, materializer,
  and handoff builders;
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
