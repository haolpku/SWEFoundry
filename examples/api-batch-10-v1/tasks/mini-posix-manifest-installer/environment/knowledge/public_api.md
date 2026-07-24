# Public API contract

Package: `posix_manifest_installer`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-validate-deployment-manifest

Public API:
- `class ManifestEntry:`
- `def load_deploy_manifest(path: str) -> list[ManifestEntry]`

Public behavior cases:
- `valid-two-file-manifest`
- `dotdot-destination-rejected`

## Step 2: 2-plan-atomic-install-operations

Public API:
- `class InstallOp:`
- `def plan_install(root: str, entries: list[ManifestEntry]) -> list[InstallOp]`

Public behavior cases:
- `new-file-copy-plan`
- `unchanged-file-noop`

## Step 3: 3-write-and-replay-intent-records

Public API:
- `class RecoveryError(Exception):`
- `def write_intent_log(path: str, ops: list[InstallOp]) -> None`
- `def replay_intent_log(root: str, log_path: str) -> list[str]`

Public behavior cases:
- `replay-completes-pending-copy`
- `second-replay-is-idempotent`

## Step 4: 4-plan-rollback-from-manifest

Public API:
- `class RollbackPlan:`
- `def plan_rollback(root: str, log_path: str) -> RollbackPlan`

Public behavior cases:
- `rollback-restores-replaced-file`
- `missing-backup-reported`

## Step 5: 5-integrated-safe-install-audit

Public API:
- `class InstallAuditReport:`
- `def audit_install(root: str, manifest_path: str, log_path: str) -> InstallAuditReport`

Public behavior cases:
- `clean-install-audit`
- `partial-install-recovery-audit`
