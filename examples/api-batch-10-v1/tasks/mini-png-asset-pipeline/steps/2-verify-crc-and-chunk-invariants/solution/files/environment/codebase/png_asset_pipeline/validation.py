from __future__ import annotations

from dataclasses import dataclass
import zlib

from .chunks import PngChunk


@dataclass(frozen=True, order=True)
class PngProblem:
    offset: int
    code: str
    chunk_type: str
    message: str


def _crc(chunk: PngChunk) -> int:
    return zlib.crc32(chunk.type_bytes + chunk.data) & 0xFFFFFFFF


def validate_png_chunks(chunks: list[PngChunk]) -> list[PngProblem]:
    problems: list[PngProblem] = []
    ihdr_count = 0
    plte_count = 0
    iend_count = 0
    seen_ihdr = False
    seen_plte = False
    seen_idat = False
    idat_closed = False
    seen_iend = False

    for index, chunk in enumerate(chunks):
        if _crc(chunk) != chunk.crc:
            problems.append(PngProblem(chunk.offset, "CRC_MISMATCH", chunk.type, "chunk CRC does not match type and data"))

        if chunk.type == "IHDR":
            ihdr_count += 1
            if index != 0:
                problems.append(PngProblem(chunk.offset, "IHDR_NOT_FIRST", chunk.type, "IHDR must be the first chunk"))
            if ihdr_count > 1:
                problems.append(PngProblem(chunk.offset, "DUPLICATE_IHDR", chunk.type, "IHDR may appear only once"))
            seen_ihdr = True
        elif not seen_ihdr:
            problems.append(PngProblem(chunk.offset, "CHUNK_BEFORE_IHDR", chunk.type, "chunks may not appear before IHDR"))

        if chunk.type == "PLTE":
            plte_count += 1
            if plte_count > 1:
                problems.append(PngProblem(chunk.offset, "DUPLICATE_PLTE", chunk.type, "PLTE may appear only once"))
            if seen_idat:
                problems.append(PngProblem(chunk.offset, "PLTE_AFTER_IDAT", chunk.type, "PLTE must precede IDAT"))
            seen_plte = True

        if chunk.type == "IDAT":
            if not seen_ihdr:
                problems.append(PngProblem(chunk.offset, "IDAT_BEFORE_IHDR", chunk.type, "IDAT must follow IHDR"))
            if idat_closed:
                problems.append(PngProblem(chunk.offset, "NONCONSECUTIVE_IDAT", chunk.type, "IDAT chunks must be consecutive"))
            seen_idat = True

        if seen_idat and chunk.type not in {"IDAT", "IEND"}:
            idat_closed = True

        if chunk.type == "IEND":
            iend_count += 1
            if chunk.length != 0:
                problems.append(PngProblem(chunk.offset, "IEND_NOT_EMPTY", chunk.type, "IEND must have zero length"))
            if iend_count > 1:
                problems.append(PngProblem(chunk.offset, "DUPLICATE_IEND", chunk.type, "IEND may appear only once"))
            if index != len(chunks) - 1:
                problems.append(PngProblem(chunk.offset, "IEND_NOT_LAST", chunk.type, "IEND must be the final chunk"))
            seen_iend = True
        elif seen_iend:
            problems.append(PngProblem(chunk.offset, "CHUNK_AFTER_IEND", chunk.type, "no chunks may follow IEND"))

    if not chunks:
        problems.append(PngProblem(8, "EMPTY_PNG", "", "PNG contains no chunks"))
    if chunks and chunks[0].type != "IHDR":
        problems.append(PngProblem(chunks[0].offset, "IHDR_NOT_FIRST", chunks[0].type, "IHDR must be the first chunk"))
    if iend_count == 0:
        last = chunks[-1].end_offset if chunks else 8
        problems.append(PngProblem(last, "MISSING_IEND", "", "PNG must terminate with IEND"))
    return sorted(set(problems))
