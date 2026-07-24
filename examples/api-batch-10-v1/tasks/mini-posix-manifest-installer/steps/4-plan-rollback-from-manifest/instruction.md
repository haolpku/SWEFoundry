Step 4 verification: rollback planning from recorded intent state.

Required public API: class RollbackPlan, class RecoveryError, plan_install, write_intent_log, replay_intent_log, and plan_rollback(root: str, log_path: str) -> RollbackPlan.

Disclosed hidden behavioral names for this step: backup digest validation, delete versus restore semantics, error aggregation. Deterministic fault protected by fp4_trusts_backup_name: assumes a backup is valid when the expected filename exists without verifying its digest.

The verifier is black-box: it imports only the installed public package in isolated Python subprocesses and never reads candidate source.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_04_smoke.py`.
