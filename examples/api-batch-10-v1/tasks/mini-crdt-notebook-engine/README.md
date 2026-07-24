# CRDT Notebook Operation Merge and Compaction Engine

`mini-crdt-notebook-engine` is a five-step, offline Greenfield terminal benchmark candidate in
the `collaborative document synchronization` domain.

The five cumulative Steps are:

1. `1-parse-immutable-operations`
2. `2-validate-causal-dag`
3. `3-merge-notebook-text-deterministically`
4. `4-compute-frontiers-and-compaction-plan`
5. `5-integrated-notebook-recovery-and-migration`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
41 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://github.com/automerge/automerge (MIT); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
