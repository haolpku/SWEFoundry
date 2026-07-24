# Step 1: Parse iCalendar components

Implement `parse_icalendar(text: str) -> list[IcalEvent]` and the public `IcalEvent` record behavior. The black-box contract covers folded content line unfolding, parameter parsing, canonical UID ordering, VEVENT properties, UID, DTSTART, DTEND, RRULE, SEQUENCE, STATUS, recurrence identity sorting, validation errors, and immutable returned records.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_01_smoke.py`.
