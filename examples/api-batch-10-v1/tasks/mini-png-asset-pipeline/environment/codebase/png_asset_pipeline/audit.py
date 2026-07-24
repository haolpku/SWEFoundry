from __future__ import annotations

from dataclasses import dataclass, field

from .chunks import PngChunk, parse_png_chunks
from .cleanup import PngCleanupAction, plan_png_cleanup
from .metadata import PngMetadata, extract_png_metadata
from .validation import PngProblem, validate_png_chunks


@dataclass(frozen=True)
class PngAuditReport:
    chunks: list[PngChunk] = field(default_factory=list)
    problems: list[PngProblem] = field(default_factory=list)
    metadata: PngMetadata | None = None
    cleanup_actions: list[PngCleanupAction] = field(default_factory=list)
    recovery_guidance: list[str] = field(default_factory=list)
    parse_error: str | None = None


def audit_png(data: bytes) -> PngAuditReport:
    chunks = parse_png_chunks(data)
    metadata = extract_png_metadata(chunks)
    return PngAuditReport(chunks=chunks, problems=validate_png_chunks(chunks), metadata=metadata, cleanup_actions=plan_png_cleanup(chunks))
