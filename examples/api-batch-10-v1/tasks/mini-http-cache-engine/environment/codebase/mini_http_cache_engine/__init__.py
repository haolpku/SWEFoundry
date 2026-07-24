"""Offline HTTP cache semantics engine benchmark package."""

from .exceptions import CacheEngineError, CachePolicyError, SnapshotRecoveryError, UnsafeMethodError
from .models import FreshnessDecision, HttpCacheAuditReport, HttpCacheEntry, InvalidationResult
from .core import audit_http_cache, build_cache_key, evaluate_http_freshness, invalidate_http_cache, merge_http_304

__all__ = [
    "CacheEngineError",
    "CachePolicyError",
    "SnapshotRecoveryError",
    "UnsafeMethodError",
    "FreshnessDecision",
    "HttpCacheAuditReport",
    "HttpCacheEntry",
    "InvalidationResult",
    "audit_http_cache",
    "build_cache_key",
    "evaluate_http_freshness",
    "invalidate_http_cache",
    "merge_http_304",
]
