"""Explicit exceptions for the offline DNS zone auditor."""

class DnsZoneError(Exception):
    """Base class for package-specific DNS zone errors."""

class ZoneParseError(ValueError, DnsZoneError):
    """Raised when restricted master-file input is malformed."""

class ZoneValidationError(DnsZoneError):
    """Raised by callers that elect to make validation problems fatal."""
