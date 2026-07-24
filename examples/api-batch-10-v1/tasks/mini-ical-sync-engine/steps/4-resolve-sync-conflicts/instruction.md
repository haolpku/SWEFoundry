# Step 4: Resolve sync conflicts

Implement `resolve_ical_conflicts(candidates: list[IcalEvent]) -> list[IcalConflictDecision]`. The black-box contract covers deterministic conflict grouping by UID and recurrence identity, sequence comparison, explicit updated timestamp tie-breaks, tombstone status precedence, UID and recurrence identity tie-break determinism, recurrence override conflicts, stable explanations, tombstone stability, and read-only input state.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_04_smoke.py`.
