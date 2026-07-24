# How to verify this handoff

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
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=infra/src python3 -m terminal_data_factory.batch_qa   --root tasks   --output ../api-batch-10-recheck.json   --limit 10   --repeats 2   --timeout 180
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
