"""Explicit exception classes for the manifest installer."""


class ManifestError(ValueError):
    """Raised when a deployment manifest is structurally invalid."""


class RecoveryError(Exception):
    """Raised when deterministic replay encounters an impossible state."""
