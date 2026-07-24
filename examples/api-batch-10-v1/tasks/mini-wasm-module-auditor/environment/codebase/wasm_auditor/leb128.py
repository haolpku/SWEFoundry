"""Small deterministic LEB128 helpers used by the starter implementation."""

from __future__ import annotations


def read_u32_leb(data: bytes, offset: int, limit: int | None = None) -> tuple[int, int]:
    """Read an unsigned LEB128 value.

    Starter behavior is intentionally incomplete: it does not fully enforce the
    five-byte u32 bound and will be replaced in step 1.
    """
    end = len(data) if limit is None else min(limit, len(data))
    result = 0
    shift = 0
    pos = offset
    while pos < end:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if byte < 0x80:
            return result, pos
        shift += 7
    raise ValueError("truncated unsigned LEB128")


def read_name(data: bytes, offset: int, limit: int | None = None) -> tuple[str, int]:
    end = len(data) if limit is None else min(limit, len(data))
    size, pos = read_u32_leb(data, offset, end)
    stop = pos + size
    if stop > end:
        raise ValueError("truncated name")
    try:
        return data[pos:stop].decode("utf-8"), stop
    except UnicodeDecodeError as exc:
        raise ValueError("invalid UTF-8 name") from exc
