from __future__ import annotations

from dataclasses import dataclass, field
import struct

from .chunks import PngChunk


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


def extract_png_metadata(chunks: list[PngChunk]) -> PngMetadata:
    ihdr = next((chunk for chunk in chunks if chunk.type == "IHDR"), None)
    if ihdr is None or len(ihdr.data) != 13:
        raise ValueError("IHDR chunk is required")
    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", ihdr.data)
    text: dict[str, str] = {}
    for chunk in chunks:
        if chunk.type == "tEXt" and b"\x00" in chunk.data:
            key, value = chunk.data.split(b"\x00", 1)
            text[key.decode("latin-1")] = value.decode("latin-1")
    return PngMetadata(width, height, bit_depth, color_type, compression, filter_method, interlace, text)
