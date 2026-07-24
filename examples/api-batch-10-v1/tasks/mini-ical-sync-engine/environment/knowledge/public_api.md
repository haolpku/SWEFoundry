# Public API contract

Package: `mini_ical_sync_engine`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-icalendar-components

Public API:
- `class IcalEvent:`
- `def parse_icalendar(text: str) -> list[IcalEvent]`

Public behavior cases:
- `folded-summary-parses`
- `missing-uid-raises`

## Step 2: 2-expand-bounded-recurrences

Public API:
- `class IcalOccurrence:`
- `def expand_ical_recurrences(events: list[IcalEvent], start: str, end: str) -> list[IcalOccurrence]`

Public behavior cases:
- `daily-count-expanded`
- `exdate-removes-occurrence`

## Step 3: 3-apply-incremental-sync-changes

Public API:
- `class IcalSyncChange:`
- `def apply_ical_sync(base: list[IcalEvent], changes: list[IcalSyncChange]) -> list[IcalEvent]`

Public behavior cases:
- `higher-sequence-update-wins`
- `delete-tombstone-hides-event`

## Step 4: 4-resolve-sync-conflicts

Public API:
- `class IcalConflictDecision:`
- `def resolve_ical_conflicts(candidates: list[IcalEvent]) -> list[IcalConflictDecision]`

Public behavior cases:
- `sequence-breaks-conflict`
- `tombstone-wins-on-newer-update`

## Step 5: 5-integrated-calendar-sync-recovery

Public API:
- `class IcalSyncAuditReport:`
- `def audit_ical_sync(snapshot: str, incoming: str, window_start: str, window_end: str) -> IcalSyncAuditReport`

Public behavior cases:
- `incremental-sync-audit`
- `snapshot-migration-audit`
