"""Explicit exceptions for the offline cache engine."""


class CacheEngineError(Exception):
    """Base class for deterministic cache-engine failures."""


class CachePolicyError(CacheEngineError, ValueError):
    """Raised when supplied HTTP metadata cannot be cached safely."""


class UnsafeMethodError(CachePolicyError):
    """Raised when a request method is not cacheable by this offline engine."""


class SnapshotRecoveryError(CacheEngineError):
    """Raised by callers that choose to treat snapshot recovery as fatal."""
