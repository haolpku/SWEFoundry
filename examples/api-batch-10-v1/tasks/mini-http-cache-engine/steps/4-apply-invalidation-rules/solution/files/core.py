"""Step 4 solution: deterministic unsafe-method and policy invalidation."""

from __future__ import annotations

from .models import FreshnessDecision, HttpCacheAuditReport, HttpCacheEntry, InvalidationResult
from .models import audit_snapshot, canonical_key, evaluate_entry, invalidate_entries, merge_304


def build_cache_key(request: dict[str, str], response: dict[str, str]) -> str:
    return canonical_key(request, response, include_vary=True)


def evaluate_http_freshness(entry: HttpCacheEntry, now: int) -> FreshnessDecision:
    return evaluate_entry(entry, now, max_age_precedence=True)


def merge_http_304(entry: HttpCacheEntry, response_304: dict[str, str]) -> HttpCacheEntry:
    return merge_304(entry, response_304, preserve_body=True)


def invalidate_http_cache(entries: list[HttpCacheEntry], event: dict[str, str]) -> InvalidationResult:
    return invalidate_entries(entries, event, all_variants=True)


def audit_http_cache(snapshot_path: str, events: list[dict[str, str]], now: int) -> HttpCacheAuditReport:
    return audit_snapshot(snapshot_path, events, now, validate_first=False)
