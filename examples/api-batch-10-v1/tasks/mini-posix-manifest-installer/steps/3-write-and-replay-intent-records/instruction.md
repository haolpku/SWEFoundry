Step 3 verification: deterministic intent logs and idempotent replay.

Required public API: class ManifestEntry, class InstallOp, class RecoveryError, plan_install, write_intent_log(path: str, ops: list[InstallOp]) -> None, and replay_intent_log(root: str, log_path: str) -> list[str].

Disclosed hidden behavioral names for this step: durable replay, idempotency, impossible state detection. Deterministic fault protected by fp3_nonidempotent_replay: fails when replay is invoked after all operations have already completed.

The verifier is black-box: it imports only the installed public package in isolated Python subprocesses and never reads candidate source.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_03_smoke.py`.
