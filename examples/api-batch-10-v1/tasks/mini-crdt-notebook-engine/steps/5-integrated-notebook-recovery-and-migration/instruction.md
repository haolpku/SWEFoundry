# Step 5 verification: Integrated notebook recovery and migration

Run `tests/test.sh` from the repository root, or set `TDF_WORKSPACE`, `TDF_TESTS_DIR`, and `TDF_REWARD_DIR` explicitly.

The verifier is black-box: it imports the candidate package only inside isolated `python -I` subprocesses and never inspects candidate source.

Disclosed behavioral checks:

1. `journal_only_audit_runs_full_pipeline`
2. `snapshot_schema_migration_recovers_combined_state`
3. `invalid_journal_missing_dependency_blocks_visible_cells`
4. `duplicate_actor_sequence_regression_still_raises`
5. `causal_cycle_regression_reported_in_audit`
6. `deterministic_merge_regression_preserved_in_audit`
7. `compaction_regression_unseen_delete_retains_source`
8. `steps_one_to_four_public_regressions_remain_available`
9. `read_only_state_check_audit_does_not_mutate_frontiers`

Hidden category names disclosed by this contract: steps 1-4 regression, snapshot compaction safety, schema migration compatibility.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_05_smoke.py`.
