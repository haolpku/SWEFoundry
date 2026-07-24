"""Explicit exception types for the mini iCalendar sync engine."""


class IcalError(Exception):
    """Base class for deterministic iCalendar benchmark errors."""


class IcalParseError(IcalError):
    """Raised when input text is not valid for the supported iCalendar subset."""


class IcalValidationError(IcalError):
    """Raised when otherwise parsed data violates the public contract."""
