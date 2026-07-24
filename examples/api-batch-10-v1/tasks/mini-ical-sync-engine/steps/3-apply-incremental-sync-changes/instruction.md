# Step 3: Apply incremental sync changes

Implement `apply_ical_sync(base: list[IcalEvent], changes: list[IcalSyncChange]) -> list[IcalEvent]`. The black-box contract covers create, update, delete tombstone changes, UID and recurrence identity keys, tombstone precedence, sequence comparison, updated timestamp comparison, change ordering independence, sorted output, and read-only input state.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_03_smoke.py`.
