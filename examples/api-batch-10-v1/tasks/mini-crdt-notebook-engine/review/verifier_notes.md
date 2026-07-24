# Verifier compilation notes

The package compiler statically parsed literal `CASES` lists in all five Step
verifiers. It confirmed 41 named cases:

- `1-parse-immutable-operations`: 8
- `2-validate-causal-dag`: 8
- `3-merge-notebook-text-deterministically`: 8
- `4-compute-frontiers-and-compaction-plan`: 8
- `5-integrated-notebook-recovery-and-migration`: 9

This number is conservative: dynamic or implicit assertions are not counted.

The delivered `verifier/audit-report.json` passed the progressive Starter, cumulative Step 1..N Oracle, public-contract smoke, five Step-specific mutant, and subprocess-isolation gates. Independent batch QA reconstructed every cumulative solution without calling the task audit, then reproduced the audit twice with an identical report hash. Harbor Oracle/Nop jobs and target-agent rollouts remain open; difficulty is therefore uncalibrated.
