# Architecture and semantic boundaries

Build Offline DNS Zone Parser and Delegation Integrity Auditor as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-zone-master-files

Parse a restricted RFC 1035 master-file syntax including origin, TTL, SOA, NS, A, AAAA, CNAME, and TXT, return canonical owner-name sorted records, and raise ValueError for malformed directives.

Verifier semantic categories:
- owner inheritance
- ttl defaults
- canonical name casing

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-validate-zone-integrity

Validate SOA uniqueness, CNAME exclusivity, apex NS presence, delegation glue requirements, and duplicate records, returning ZoneProblem values sorted by owner, severity, and type.

Verifier semantic categories:
- duplicate RR detection
- delegation glue
- severity ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-simulate-offline-dns-answers

Answer deterministic offline queries for supported RR types, follow bounded CNAME chains, return NOERROR, NXDOMAIN, or CNAME_LOOP, and never use sockets or externally observed resolver state.

Verifier semantic categories:
- rcode semantics
- cname loop detection
- answer ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-plan-serial-and-digest-migration

Compute a deterministic migration plan that increments SOA serials, normalizes TTLs, and writes local record-set sha256 digests for replayable integrity verification without mutating record inputs.

Verifier semantic categories:
- serial arithmetic
- digest canonicalization
- idempotent planning

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-zone-audit

Integrate parsing, validation, offline answers, and migration into ZoneAuditReport, preserve steps 1 through 4 outputs, and produce deterministic read-only validation and replayable recovery results.

Verifier semantic categories:
- steps 1-4 regression
- offline protocol behavior
- canonical report ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
