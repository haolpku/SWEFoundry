from __future__ import annotations

from dataclasses import dataclass
import struct

from .exceptions import PngFormatError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True, order=True)
class PngChunk:
    offset: int
    length: int
    type: str
    data: bytes
    crc: int

    @property
    def end_offset(self) -> int:
        return self.offset + 12 + self.length

    @property
    def type_bytes(self) -> bytes:
        return self.type.encode("ascii")


def _validate_chunk_type(type_bytes: bytes) -> str:
    if len(type_bytes) != 4:
        raise PngFormatError("chunk type must be four bytes")
    if not all(65 <= b <= 90 or 97 <= b <= 122 for b in type_bytes):
        raise PngFormatError("chunk type must contain ASCII letters only")
    return type_bytes.decode("ascii")


def parse_png_chunks(data: bytes) -> list[PngChunk]:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    data = bytes(data)
    if not data.startswith(PNG_SIGNATURE):
        raise PngFormatError("missing PNG signature")
    chunks: list[PngChunk] = []
    offset = len(PNG_SIGNATURE)
    seen_iend = False
    while offset < len(data):
        if offset + 8 > len(data):
            raise PngFormatError("truncated chunk header")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = _validate_chunk_type(data[offset + 4:offset + 8])
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if data_end > len(data):
            raise PngFormatError("truncated chunk data")
        if crc_end > len(data):
            raise PngFormatError("truncated chunk CRC")
        crc = struct.unpack(">I", data[data_end:crc_end])[0]
        chunks.append(PngChunk(offset, length, chunk_type, data[data_start:data_end], crc))
        offset = crc_end
        if chunk_type == "IEND":
            seen_iend = True
            break
    if not seen_iend:
        raise PngFormatError("missing IEND chunk")
    if offset != len(data):
        raise PngFormatError("trailing bytes after IEND")
    return chunks
