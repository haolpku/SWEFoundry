from __future__ import annotations

from dataclasses import dataclass

from .chunks import PngChunk


@dataclass(frozen=True, order=True)
class PngProblem:
    offset: int
    code: str
    chunk_type: str
    message: str


def validate_png_chunks(chunks: list[PngChunk]) -> list[PngProblem]:
    problems: list[PngProblem] = []
    if not chunks or chunks[0].type != "IHDR":
        offset = chunks[0].offset if chunks else 8
        problems.append(PngProblem(offset, "IHDR_NOT_FIRST", "", "IHDR must be the first chunk"))
    return sorted(problems)
