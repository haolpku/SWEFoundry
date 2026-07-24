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


def parse_png_chunks(data: bytes) -> list[PngChunk]:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    data = bytes(data)
    if not data.startswith(PNG_SIGNATURE):
        raise PngFormatError("missing PNG signature")
    chunks: list[PngChunk] = []
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        if offset + 8 > len(data):
            raise PngFormatError("truncated chunk header")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        type_bytes = data[offset + 4:offset + 8]
        try:
            chunk_type = type_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise PngFormatError("chunk type is not ASCII") from exc
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        # Starter is intentionally incomplete: it stops instead of rejecting a
        # declared chunk length that extends past the available byte buffer.
        if crc_end > len(data):
            break
        crc = struct.unpack(">I", data[data_end:crc_end])[0]
        chunks.append(PngChunk(offset, length, chunk_type, data[data_start:data_end], crc))
        offset = crc_end
        if chunk_type == "IEND":
            return chunks
    raise PngFormatError("missing IEND chunk")
