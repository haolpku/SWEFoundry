# Architecture and semantic boundaries

Build Atomic Filesystem Manifest Installer as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-validate-deployment-manifest

Load a JSON deployment manifest, normalize relative POSIX destination paths, reject traversal and duplicate destinations with ValueError, validate declared sha256 fields, and return entries sorted by destination path.

Verifier semantic categories:
- path normalization
- duplicate destination detection
- canonical ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-plan-atomic-install-operations

Compare manifest entries with an installation root, verify source digests, and create an ordered operation plan using temporary paths, directory preparation, backups, and atomic renames without modifying the filesystem.

Verifier semantic categories:
- digest integrity
- directory creation ordering
- read-only planning

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-write-and-replay-intent-records

Implement deterministic intent log serialization for planned operations and replay it idempotently against the root, returning completed operation identifiers and raising RecoveryError for impossible partial states.

Verifier semantic categories:
- durable replay
- idempotency
- impossible state detection

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-plan-rollback-from-manifest

Generate a rollback plan from recorded previous digests and backup files, verify backup integrity by content digest, and return explicit missing-backup errors without applying the rollback.

Verifier semantic categories:
- backup digest validation
- delete versus restore semantics
- error aggregation

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-safe-install-audit

Integrate manifest loading, planning, intent replay, and rollback planning into InstallAuditReport, preserve all behavior from steps 1 through 4, and report deterministic crash recovery outcomes before fresh planning.

Verifier semantic categories:
- steps 1-4 regression
- atomicity model
- read-only versus replay behavior

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
