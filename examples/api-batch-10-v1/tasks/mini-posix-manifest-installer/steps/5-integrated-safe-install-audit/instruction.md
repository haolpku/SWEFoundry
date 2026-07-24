Step 5 verification: integrated recovery-first install audit.

Required public API: class InstallAuditReport and audit_install(root: str, manifest_path: str, log_path: str) -> InstallAuditReport, while preserving all public behavior from steps 1 through 4.

Disclosed hidden behavioral names for this step: steps 1-4 regression, atomicity model, read-only versus replay behavior. Deterministic fault protected by fp5_plans_before_recovery: computes a fresh install plan before replaying an existing intent log, producing incorrect recovery results.

The verifier is black-box: it imports only the installed public package in isolated Python subprocesses and never reads candidate source. Step 5 checks integrated recovery and migration semantics and critical regressions for Steps 1-4.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_05_smoke.py`.
