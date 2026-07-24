# Architecture and semantic boundaries

Build Offline HTTP Cache Semantics Engine as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-canonicalize-requests-and-responses

Parse request and response dictionaries into cache entries, normalize method, scheme, host, path, query, and headers, reject unsafe cacheable method combinations, and return canonical keys deterministically.

Verifier semantic categories:
- header canonicalization
- query ordering
- method cacheability

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-evaluate-freshness-and-stale-policy

Evaluate Cache-Control, Expires, Age, Date, ETag, and Last-Modified metadata using an injected integer now value, returning fresh, stale, or unusable decisions without wall-clock access.

Verifier semantic categories:
- directive precedence
- injected clock only
- stale-if-error handling

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-merge-conditional-304-responses

Merge a cached response with an offline conditional 304 response, update allowed headers, preserve entity body and validators, and raise ValueError for mismatched cache validators.

Verifier semantic categories:
- validator matching
- header merge rules
- body preservation

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-apply-invalidation-rules

Apply offline invalidation for unsafe methods, explicit purge records, no-store policy, and stale reuse settings, returning affected cache keys sorted lexically without consulting any external service.

Verifier semantic categories:
- unsafe method invalidation
- variant invalidation
- stable affected ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-cache-audit-and-recovery

Integrate key construction, freshness evaluation, 304 merging, invalidation, stale policy, and disk snapshot recovery into HttpCacheAuditReport, preserve steps 1 through 4 behavior, and report deterministic recovery actions.

Verifier semantic categories:
- steps 1-4 regression
- disk recovery
- variant consistency

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
