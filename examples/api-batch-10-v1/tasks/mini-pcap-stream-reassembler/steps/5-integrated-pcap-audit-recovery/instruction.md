Step 5 verification contract: integrate parsing, protocol decoding, stream reassembly, timeout generation, checkpoint replay, migration, and deterministic truncation recovery while preserving Steps 1-4. Disclosed black-box behavioral gates are complete_stream_audit_public_integrated, truncated_capture_recovery_public_preserves_partial_stream, checkpoint_replay_migration_hidden, step1_big_endian_regression_hidden, step2_ipv4_options_regression_hidden, step3_out_of_order_regression_hidden, step4_all_open_flows_timeout_regression_hidden, invalid_checkpoint_raises_checkpoint_error_hidden, and read_only_state_integrated_audit_no_mutation.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_05_smoke.py`.
