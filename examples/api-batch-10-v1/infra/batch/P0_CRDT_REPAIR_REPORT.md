# P0 CRDT progressive-Oracle repair

## Reproduction

The expert finding was valid. An independent runner created a clean workspace
for every Step, installed solutions 1..N, and then ran the public smoke and
strict verifier:

| Step | Public smoke | Verifier correctness | Result |
|---:|---:|---:|---|
| 1 | pass | 1.0 | pass |
| 2 | pass | 1.0 | pass |
| 3 | fail | 0.0 | fail |
| 4 | fail | 0.0 | fail |
| 5 | pass | 1.0 | pass |

The real pre-fix cumulative result was therefore 3/5 tasks Steps and 48/50
public smokes across the batch.

## Root cause

Step 3 and Step 4 solution payloads were patch-like `engine.py` files that
imported the module they were replacing. They were not full cumulative modules.
The starter `__init__.py` also exported later APIs before their Step.

The task audit hid both failures: its `_install_oracle` installed the Step 5
solution for Step 3 and Step 4 instead of installing solutions 1..N.

The first batch QA repeated each task's audit and trusted its `passed` field, so
it shared the same blind spot.

## Repair

- Step 3 is now a complete cumulative Step 1–3 module.
- Step 4 is now a complete cumulative Step 1–4 module.
- Starter and Step 1–5 package exports are progressive.
- Every solution installs both `engine.py` and `__init__.py`.
- The CRDT audit executes solution Steps 1..N for every Oracle gate.
- The CRDT audit adds five cumulative public-smoke gates.
- Batch QA independently reconstructs every Step without calling task audit.
- Batch QA independently counts named checks, public smokes, and Step-specific
  mutants from source.

## Post-fix evidence

| Step | Public smoke | Verifier correctness | Result |
|---:|---:|---:|---|
| 1 | pass | 1.0 | pass |
| 2 | pass | 1.0 | pass |
| 3 | pass | 1.0 | pass |
| 4 | pass | 1.0 | pass |
| 5 | pass | 1.0 | pass |

The repaired CRDT audit passes 21/21 gates: five Starter, five cumulative
Oracle, five cumulative public-smoke, five mutant, and one isolation gate.

Machine-readable before/after traces and the deterministic repair operator are
included under `evidence/generation/` and `evidence/repairs/`.

Harbor execution, target-agent rollout, difficulty calibration, and expert
semantic/license approval remain open.
