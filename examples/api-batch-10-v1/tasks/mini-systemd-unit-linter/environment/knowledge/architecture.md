# Architecture and semantic boundaries

Build Systemd Unit Dependency Linter and Boot Plan Simulator as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-unit-files-deterministically

Parse a restricted systemd unit syntax from supplied directories, preserve section and key semantics, return units sorted by normalized name, and raise ValueError for duplicate scalar keys or malformed section headers.

Verifier semantic categories:
- canonical unit names
- comment handling
- duplicate detection

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-validate-dependency-integrity

Validate Requires, Wants, After, Before, and Conflicts edges only against loaded units, return sorted UnitProblem objects with stable severity, and never inspect paths outside the supplied roots.

Verifier semantic categories:
- edge type severity
- root confinement
- problem ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-compute-boot-activation-order

Compute a canonical topological activation plan for the requested target closure, honor ordering dependencies and conflicts, and raise DependencyCycleError with a sorted cycle witness when planning is impossible.

Verifier semantic categories:
- cycle determinism
- conflict exclusion
- target closure

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-replay-failure-recovery

Simulate deterministic start replay using a supplied activation plan and configured failed units, propagate required dependency failures, respect restart limit fields, and return explicit started, skipped, and failed sets in lexical order.

Verifier semantic categories:
- failure propagation
- restart limit semantics
- canonical set output

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-unit-audit

Integrate loading, validation, activation planning, and replay into a read-only UnitAuditReport, preserve all observable outputs from steps 1 through 4, and return deterministic recovery summaries for the requested target.

Verifier semantic categories:
- steps 1-4 regression
- read-only validation
- exception mapping

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
