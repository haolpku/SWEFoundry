# Public API contract

Package: `crdtnotebook`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-immutable-operations

Public API:
- `class NotebookOp:`
- `def parse_notebook_ops(text: str) -> list[NotebookOp]`

Public behavior cases:
- `two-actor-inserts-parse`
- `duplicate-actor-sequence-raises`

## Step 2: 2-validate-causal-dag

Public API:
- `class CrdtProblem:`
- `def validate_notebook_dag(ops: list[NotebookOp]) -> list[CrdtProblem]`

Public behavior cases:
- `missing-dependency-reported`
- `causal-cycle-reported`

## Step 3: 3-merge-notebook-text-deterministically

Public API:
- `class NotebookCell:`
- `def merge_notebook_text(ops: list[NotebookOp]) -> list[NotebookCell]`

Public behavior cases:
- `concurrent-inserts-ordered`
- `delete-leaves-tombstone`

## Step 4: 4-compute-frontiers-and-compaction-plan

Public API:
- `class CrdtCompactionPlan:`
- `def plan_notebook_compaction(ops: list[NotebookOp], peer_frontiers: dict[str, list[str]]) -> CrdtCompactionPlan`

Public behavior cases:
- `stable-tombstone-compacted`
- `unseen-operation-retained`

## Step 5: 5-integrated-notebook-recovery-and-migration

Public API:
- `class CrdtNotebookAuditReport:`
- `def audit_crdt_notebook(snapshot: str | None, journal: str, peer_frontiers: dict[str, list[str]]) -> CrdtNotebookAuditReport`

Public behavior cases:
- `journal-only-audit`
- `snapshot-schema-migration-audit`
