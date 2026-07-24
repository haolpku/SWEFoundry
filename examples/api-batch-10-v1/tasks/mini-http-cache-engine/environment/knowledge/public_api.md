# Public API contract

Package: `mini_http_cache_engine`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-canonicalize-requests-and-responses

Public API:
- `class HttpCacheEntry:`
- `def build_cache_key(request: dict[str, str], response: dict[str, str]) -> str`

Public behavior cases:
- `host-case-normalized`
- `vary-header-in-key`

## Step 2: 2-evaluate-freshness-and-stale-policy

Public API:
- `class FreshnessDecision:`
- `def evaluate_http_freshness(entry: HttpCacheEntry, now: int) -> FreshnessDecision`

Public behavior cases:
- `max-age-fresh`
- `expired-response-stale`

## Step 3: 3-merge-conditional-304-responses

Public API:
- `def merge_http_304(entry: HttpCacheEntry, response_304: dict[str, str]) -> HttpCacheEntry`

Public behavior cases:
- `etag-304-merge`
- `mismatched-etag-raises`

## Step 4: 4-apply-invalidation-rules

Public API:
- `class InvalidationResult:`
- `def invalidate_http_cache(entries: list[HttpCacheEntry], event: dict[str, str]) -> InvalidationResult`

Public behavior cases:
- `post-invalidates-uri`
- `no-store-not-retained`

## Step 5: 5-integrated-cache-audit-and-recovery

Public API:
- `class HttpCacheAuditReport:`
- `def audit_http_cache(snapshot_path: str, events: list[dict[str, str]], now: int) -> HttpCacheAuditReport`

Public behavior cases:
- `fresh-cache-audit`
- `truncated-snapshot-recovery`
