# Architecture and semantic boundaries

Build Deterministic iCalendar Incremental Sync Engine as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-icalendar-components

Parse VCALENDAR text with folded content lines, VEVENT components, properties, parameters, UID, DTSTART, DTEND, RRULE, SEQUENCE, and STATUS, returning events sorted by UID and recurrence identity.

Verifier semantic categories:
- line unfolding
- parameter parsing
- canonical UID ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-expand-bounded-recurrences

Expand supported daily, weekly, count, until, interval, and exception-date recurrences inside explicit start and end bounds, returning deterministic occurrence records without using live time.

Verifier semantic categories:
- bound inclusivity
- RRULE interval handling
- exception date semantics

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-apply-incremental-sync-changes

Apply deterministic create, update, and delete tombstone changes to a calendar snapshot, compare UID and SEQUENCE values, preserve newer tombstones, and return the resulting event set sorted by UID.

Verifier semantic categories:
- tombstone precedence
- sequence comparison
- change ordering independence

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-resolve-sync-conflicts

Resolve conflicting offline edits deterministically using SEQUENCE, explicit updated timestamp strings, UID, recurrence identity, and tombstone status, returning conflict decisions with stable explanations.

Verifier semantic categories:
- tie-break determinism
- recurrence override conflicts
- tombstone stability

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-calendar-sync-recovery

Integrate parsing, bounded expansion, incremental sync, conflict resolution, tombstones, and snapshot migration into IcalSyncAuditReport, preserve steps 1 through 4 behavior, and recover deterministically from snapshot version changes.

Verifier semantic categories:
- steps 1-4 regression
- snapshot migration
- tombstone compaction safety

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
