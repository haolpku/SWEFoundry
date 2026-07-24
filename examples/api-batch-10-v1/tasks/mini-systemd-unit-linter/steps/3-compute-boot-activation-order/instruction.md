# Step 3 verification contract

Compute canonical target activation plans. The verifier is black-box and checks these disclosed names: simple_after_order, before_order_is_honored, requires_closure_includes_requirements, wants_closure_includes_wants, conflict_exclusion_raises, cycle_raises_with_sorted_witness, deterministic_lexical_order, read_only_state_check.

Expected public API: class DependencyCycleError(Exception) and def plan_activation(units: list[UnitFile], target: str) -> list[str].

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_03_smoke.py`.
