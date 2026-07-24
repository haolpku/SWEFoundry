class PngAssetError(Exception):
    """Base exception for deterministic PNG asset processing."""


class PngFormatError(ValueError, PngAssetError):
    """Raised when byte input cannot be parsed as a bounded PNG stream."""


class PngMetadataError(ValueError, PngAssetError):
    """Raised when metadata fields use unsupported encodings or methods."""
