"""Deterministic bounded LEB128 and UTF-8 helpers."""

from __future__ import annotations


def read_u32_leb(data: bytes, offset: int, limit: int | None = None) -> tuple[int, int]:
    """Read a canonical unsigned 32-bit LEB128 value.

    At most five bytes are accepted. Encodings that run past *limit*, overflow
    u32, or use non-minimal trailing continuation bytes raise ValueError.
    """
    end = len(data) if limit is None else limit
    if offset < 0 or end < offset or end > len(data):
        raise ValueError("invalid LEB128 bounds")
    result = 0
    shift = 0
    pos = offset
    for index in range(5):
        if pos >= end:
            raise ValueError("truncated unsigned LEB128")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if byte < 0x80:
            if result > 0xFFFFFFFF:
                raise ValueError("unsigned LEB128 overflows u32")
            if index > 0 and byte == 0 and result < (1 << shift):
                raise ValueError("non-canonical unsigned LEB128")
            return result, pos
        shift += 7
    raise ValueError("unsigned LEB128 exceeds five bytes")


def read_name(data: bytes, offset: int, limit: int | None = None) -> tuple[str, int]:
    end = len(data) if limit is None else limit
    size, pos = read_u32_leb(data, offset, end)
    stop = pos + size
    if stop > end:
        raise ValueError("truncated name")
    try:
        return data[pos:stop].decode("utf-8"), stop
    except UnicodeDecodeError as exc:
        raise ValueError("invalid UTF-8 name") from exc
