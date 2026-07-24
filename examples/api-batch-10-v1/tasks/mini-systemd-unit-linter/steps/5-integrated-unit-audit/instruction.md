# Step 5 verification contract

Integrate loading, validation, planning, replay, recovery summaries, read-only reports, and exception mapping. The verifier is black-box and checks these disclosed names: healthy_boot_audit_recovery_summary, cycle_keeps_validation_problems, duplicate_load_error_mapped, requires_validation_regression, before_planning_regression, wanted_failure_replay_regression, deterministic_units_and_recovery_sorted, read_only_state_check.

Expected public API: class UnitAuditReport and def audit_units(paths: list[str], target: str, failed: set[str]) -> UnitAuditReport. This final step intentionally regresses Steps 1 through 4 through the integrated API.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_05_smoke.py`.
