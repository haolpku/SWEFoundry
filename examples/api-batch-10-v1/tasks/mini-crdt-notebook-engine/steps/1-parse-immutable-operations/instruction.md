# Step 1 verification: Parse immutable operations

Run `tests/test.sh` from the repository root, or set `TDF_WORKSPACE`, `TDF_TESTS_DIR`, and `TDF_REWARD_DIR` explicitly.

The verifier is black-box: it imports the candidate package only inside isolated `python -I` subprocesses and never inspects candidate source.

Disclosed behavioral checks:

1. `sorts_two_actor_inserts_by_actor_sequence`
2. `duplicate_actor_sequence_raises`
3. `newline_delimited_json_supported`
4. `object_wrapped_operations_supported`
5. `validates_actor_sequence_and_character_contract`
6. `normalizes_dependency_and_checkpoint_cover_order`
7. `delete_and_set_title_fields_are_normalized`
8. `read_only_state_check_operation_immutability`

Hidden category names disclosed by this contract: operation immutability, actor sequence validation, canonical operation ordering.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_01_smoke.py`.
