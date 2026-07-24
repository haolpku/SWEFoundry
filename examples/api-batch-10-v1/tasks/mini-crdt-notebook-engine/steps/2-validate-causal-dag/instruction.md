# Step 2 verification: Validate causal DAG

Run `tests/test.sh` from the repository root, or set `TDF_WORKSPACE`, `TDF_TESTS_DIR`, and `TDF_REWARD_DIR` explicitly.

The verifier is black-box: it imports the candidate package only inside isolated `python -I` subprocesses and never inspects candidate source.

Disclosed behavioral checks:

1. `missing_dependency_reported_with_stable_witness`
2. `checkpoint_missing_coverage_reported`
3. `actor_sequence_gap_reported`
4. `causal_cycle_witness_deterministic`
5. `problems_sorted_stably_by_dataclass_order`
6. `valid_dag_has_no_problems`
7. `parse_duplicate_regression_still_raises`
8. `read_only_state_check_validate_does_not_mutate_ops`

Hidden category names disclosed by this contract: dependency existence, cycle witness determinism, sequence continuity.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_02_smoke.py`.
