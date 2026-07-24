# Deterministic iCalendar Incremental Sync Engine

`mini-ical-sync-engine` is a five-step, offline Greenfield terminal benchmark candidate in
the `calendar data synchronization` domain.

The five cumulative Steps are:

1. `1-parse-icalendar-components`
2. `2-expand-bounded-recurrences`
3. `3-apply-incremental-sync-changes`
4. `4-resolve-sync-conflicts`
5. `5-integrated-calendar-sync-recovery`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
41 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://www.rfc-editor.org/rfc/rfc5545 (IETF Trust Legal Provisions); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
