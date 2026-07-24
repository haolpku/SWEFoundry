Step 4 verification contract: compute deterministic timeout events from packet timestamps and close-state flags. Disclosed black-box behavioral gates are idle_flow_timeout_public, closed_flow_no_timeout_public_fin, rst_closed_flow_no_timeout_hidden, all_open_flows_reported_hidden_not_last_only, explicit_timestamp_arithmetic_hidden_no_live_time, stable_event_ordering_hidden, negative_idle_seconds_raises, and read_only_state_segments_no_mutation.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_04_smoke.py`.
