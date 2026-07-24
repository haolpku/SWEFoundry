from __future__ import annotations

from dataclasses import dataclass

from .chunks import PngChunk


@dataclass(frozen=True, order=True)
class PngCleanupAction:
    offset: int
    action: str
    chunk_type: str
    reason: str
    details: tuple[str, ...] = ()


def plan_png_cleanup(chunks: list[PngChunk]) -> list[PngCleanupAction]:
    return []
