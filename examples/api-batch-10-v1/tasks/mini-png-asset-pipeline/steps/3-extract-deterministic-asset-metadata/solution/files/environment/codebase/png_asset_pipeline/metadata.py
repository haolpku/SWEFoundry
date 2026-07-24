from __future__ import annotations

from dataclasses import dataclass, field
import struct

from .chunks import PngChunk
from .exceptions import PngMetadataError


@dataclass(frozen=True)
class PngMetadata:
    width: int
    height: int
    bit_depth: int
    color_type: int
    compression_method: int
    filter_method: int
    interlace_method: int
    text: dict[str, str] = field(default_factory=dict)


def _decode_latin1(data: bytes) -> str:
    return data.decode("latin-1")


def _text_from_text_chunk(chunk: PngChunk) -> tuple[str, str] | None:
    if b"\x00" not in chunk.data:
        return None
    key, value = chunk.data.split(b"\x00", 1)
    if not key:
        return None
    return _decode_latin1(key), _decode_latin1(value)


def _text_from_ztxt_chunk(chunk: PngChunk) -> tuple[str, str] | None:
    if b"\x00" not in chunk.data:
        return None
    key, rest = chunk.data.split(b"\x00", 1)
    if not key or not rest:
        return None
    method = rest[0]
    if method != 0:
        raise PngMetadataError("unsupported zTXt compression method")
    return _decode_latin1(key), "<compressed>"


def _text_from_itxt_chunk(chunk: PngChunk) -> tuple[str, str] | None:
    if b"\x00" not in chunk.data:
        return None
    key, rest = chunk.data.split(b"\x00", 1)
    if not key or len(rest) < 2:
        return None
    compressed_flag = rest[0]
    method = rest[1]
    if compressed_flag not in (0, 1):
        raise PngMetadataError("unsupported iTXt compression flag")
    if compressed_flag == 1 and method != 0:
        raise PngMetadataError("unsupported iTXt compression method")
    tail = rest[2:]
    parts = tail.split(b"\x00", 2)
    if len(parts) != 3:
        return None
    value = "<compressed>" if compressed_flag else parts[2].decode("utf-8", "strict")
    return _decode_latin1(key), value


def extract_png_metadata(chunks: list[PngChunk]) -> PngMetadata:
    ihdr = next((chunk for chunk in chunks if chunk.type == "IHDR"), None)
    if ihdr is None:
        raise PngMetadataError("IHDR chunk is required")
    if len(ihdr.data) != 13:
        raise PngMetadataError("IHDR chunk must contain 13 bytes")
    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", ihdr.data)
    if compression != 0:
        raise PngMetadataError("unsupported IHDR compression method")

    pairs: list[tuple[str, str]] = []
    for chunk in chunks:
        parsed: tuple[str, str] | None = None
        if chunk.type == "tEXt":
            parsed = _text_from_text_chunk(chunk)
        elif chunk.type == "zTXt":
            parsed = _text_from_ztxt_chunk(chunk)
        elif chunk.type == "iTXt":
            parsed = _text_from_itxt_chunk(chunk)
        if parsed is not None:
            pairs.append(parsed)

    canonical: dict[str, str] = {}
    for key, value in sorted(pairs, key=lambda item: (item[0], item[1])):
        if key not in canonical:
            canonical[key] = value
    return PngMetadata(width, height, bit_depth, color_type, compression, filter_method, interlace, canonical)
