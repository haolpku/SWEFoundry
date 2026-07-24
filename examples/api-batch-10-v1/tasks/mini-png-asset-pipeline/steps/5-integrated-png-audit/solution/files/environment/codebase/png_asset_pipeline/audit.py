from __future__ import annotations

from dataclasses import dataclass, field

from .chunks import PngChunk, parse_png_chunks
from .cleanup import PngCleanupAction, plan_png_cleanup
from .exceptions import PngFormatError, PngMetadataError
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


def _guidance_for_parse_error(message: str) -> list[str]:
    guidance = [
        "keep the last validated asset unchanged",
        "write future assets to a same-directory temporary file",
        "fsync and atomically publish with os.replace only after validation succeeds",
    ]
    if "truncated" in message or "missing IEND" in message:
        guidance.insert(0, "discard the incomplete candidate because PNG termination is not validated")
    return guidance


def audit_png(data: bytes) -> PngAuditReport:
    try:
        chunks = parse_png_chunks(data)
    except (PngFormatError, ValueError) as exc:
        problem = PngProblem(0, "PARSE_ERROR", "", str(exc))
        return PngAuditReport(chunks=[], problems=[problem], metadata=None, cleanup_actions=[], recovery_guidance=_guidance_for_parse_error(str(exc)), parse_error=str(exc))

    problems = validate_png_chunks(chunks)
    try:
        metadata = extract_png_metadata(chunks)
    except (PngMetadataError, ValueError) as exc:
        metadata = None
        problems = sorted(problems + [PngProblem(chunks[0].offset if chunks else 8, "METADATA_ERROR", "IHDR", str(exc))])
    cleanup_actions = plan_png_cleanup(chunks)
    guidance: list[str] = []
    if problems or cleanup_actions:
        guidance = [
            "audit is read-only; do not modify the source bytes in place",
            "create a deterministic rewrite plan from cleanup_actions before transcoding",
            "publish repaired output through a temporary file followed by os.replace",
        ]
    return PngAuditReport(chunks=chunks, problems=problems, metadata=metadata, cleanup_actions=cleanup_actions, recovery_guidance=guidance, parse_error=None)
