# Step 4 verification: Compute frontiers and compaction plan

Run `tests/test.sh` from the repository root, or set `TDF_WORKSPACE`, `TDF_TESTS_DIR`, and `TDF_REWARD_DIR` explicitly.

The verifier is black-box: it imports the candidate package only inside isolated `python -I` subprocesses and never inspects candidate source.

Disclosed behavioral checks:

1. `stable_tombstone_compacted_when_all_peers_ack_delete`
2. `unseen_delete_keeps_tombstone_source_retained`
3. `peer_frontiers_are_sorted_and_preserved`
4. `checkpoint_candidate_requires_covered_operations_seen`
5. `no_peer_frontiers_uses_local_complete_closure`
6. `unknown_frontier_ids_are_ignored_safely`
7. `retained_operations_are_stable_sorted_identifiers`
8. `read_only_state_check_compaction_does_not_mutate_inputs`

Hidden category names disclosed by this contract: frontier comparison, tombstone stability, safe checkpoint boundaries.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_04_smoke.py`.
