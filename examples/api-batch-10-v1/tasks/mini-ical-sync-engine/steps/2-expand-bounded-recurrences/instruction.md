# Step 2: Expand bounded recurrences

Implement `expand_ical_recurrences(events: list[IcalEvent], start: str, end: str) -> list[IcalOccurrence]`. The black-box contract covers daily and weekly RRULE expansion, COUNT, UNTIL inclusivity, INTERVAL handling, explicit start/end window bounds, exception date semantics, cancelled event filtering, deterministic occurrence ordering, and read-only input state.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_02_smoke.py`.
