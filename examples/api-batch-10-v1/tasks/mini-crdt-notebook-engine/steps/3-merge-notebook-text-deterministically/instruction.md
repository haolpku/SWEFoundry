# Step 3 verification: Merge notebook text deterministically

Run `tests/test.sh` from the repository root, or set `TDF_WORKSPACE`, `TDF_TESTS_DIR`, and `TDF_REWARD_DIR` explicitly.

The verifier is black-box: it imports the candidate package only inside isolated `python -I` subprocesses and never inspects candidate source.

Disclosed behavioral checks:

1. `concurrent_inserts_ordered_by_operation_identifier`
2. `concurrent_insert_result_independent_of_input_order`
3. `causal_after_chain_preserves_character_order`
4. `delete_removes_visible_character_and_keeps_tombstone`
5. `duplicate_deletes_are_idempotent`
6. `cells_sorted_by_identifier_and_titles_preserved`
7. `invalid_dag_rejected_before_merge`
8. `read_only_state_check_merge_does_not_mutate_ops`

Hidden category names disclosed by this contract: concurrent insert ordering, delete idempotency, cell ordering.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_03_smoke.py`.
