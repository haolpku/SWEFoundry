# Architecture and semantic boundaries

Build CRDT Notebook Operation Merge and Compaction Engine as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-immutable-operations

Parse JSON notebook operations for insert, delete, set-title, and checkpoint records, validate actor, sequence, dependency, object, and character fields, and return operations sorted by actor then sequence.

Verifier semantic categories:
- operation immutability
- actor sequence validation
- canonical operation ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-validate-causal-dag

Validate dependency references, actor sequence continuity, causal acyclicity, and checkpoint coverage, returning sorted CrdtProblem objects with stable witnesses for missing dependencies and cycles.

Verifier semantic categories:
- dependency existence
- cycle witness determinism
- sequence continuity

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-merge-notebook-text-deterministically

Apply valid insert and delete operations to notebook cells using causal order and stable actor-sequence tie breaks, preserve tombstoned positions, and return merged cell text sorted by cell identifier.

Verifier semantic categories:
- concurrent insert ordering
- delete idempotency
- cell ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-compute-frontiers-and-compaction-plan

Compute peer frontiers, stable tombstones, checkpoint candidates, and read-only compaction actions from acknowledged operation sets, ensuring no operation needed by any peer is removed.

Verifier semantic categories:
- frontier comparison
- tombstone stability
- safe checkpoint boundaries

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-notebook-recovery-and-migration

Integrate operation parsing, causal validation, deterministic text merge, peer frontier analysis, snapshot compaction, and schema migration into CrdtNotebookAuditReport, preserve steps 1 through 4 behavior, and recover deterministic state from snapshots and journals.

Verifier semantic categories:
- steps 1-4 regression
- snapshot compaction safety
- schema migration compatibility

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
