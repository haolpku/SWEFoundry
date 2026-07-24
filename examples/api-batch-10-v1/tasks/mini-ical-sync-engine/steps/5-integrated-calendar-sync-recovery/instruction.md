# Step 5: Integrated calendar sync recovery

Implement `audit_ical_sync(snapshot: str, incoming: str, window_start: str, window_end: str) -> IcalSyncAuditReport`. The black-box contract integrates parsing, bounded recurrence expansion, incremental sync, conflict resolution, tombstones, snapshot migration, tombstone compaction safety, and deterministic recovery from snapshot version changes. This final step also includes critical regressions for Steps 1-4: line unfolding, parameter parsing, canonical UID ordering, bound inclusivity, RRULE interval handling, exception date semantics, tombstone precedence, sequence comparison, change ordering independence, tie-break determinism, recurrence override conflicts, and tombstone stability.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_05_smoke.py`.
