"""Explicit exceptions for the PCAP reassembler package."""

class PcapReassemblerError(Exception):
    """Base class for package-specific errors."""

class PcapFormatError(PcapReassemblerError, ValueError):
    """Raised when a classic PCAP byte stream is structurally invalid."""

class ProtocolDecodeError(PcapReassemblerError, ValueError):
    """Raised when a supported protocol header is malformed."""

class CheckpointError(PcapReassemblerError, ValueError):
    """Raised when checkpoint bytes cannot be decoded safely."""
