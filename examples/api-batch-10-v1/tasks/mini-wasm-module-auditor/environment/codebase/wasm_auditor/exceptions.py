"""Explicit exception classes for wasm_auditor."""

class WasmAuditError(Exception):
    """Base class for package-specific audit failures."""


class WasmFormatError(ValueError, WasmAuditError):
    """Raised when bytes are not a well-formed restricted WebAssembly binary."""
