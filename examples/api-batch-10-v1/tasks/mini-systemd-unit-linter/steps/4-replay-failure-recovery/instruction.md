# Step 4 verification contract

Replay deterministic activation outcomes. The verifier is black-box and checks these disclosed names: required_failure_skips_dependent, wanted_failure_continues, restart_on_failure_with_burst_recovers, restart_limit_one_fails, unknown_plan_entry_is_skipped, canonical_set_output_sorted, required_skip_propagates_transitively, read_only_state_check.

Expected public API: class BootReplay and def replay_activation(units: list[UnitFile], plan: list[str], failed: set[str]) -> BootReplay.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_04_smoke.py`.
