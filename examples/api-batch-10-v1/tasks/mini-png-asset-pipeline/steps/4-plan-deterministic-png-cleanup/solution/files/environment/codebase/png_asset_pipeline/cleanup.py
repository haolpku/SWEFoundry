from __future__ import annotations

from dataclasses import dataclass
import zlib

from .chunks import PngChunk
from .metadata import extract_png_metadata


@dataclass(frozen=True, order=True)
class PngCleanupAction:
    offset: int
    action: str
    chunk_type: str
    reason: str
    details: tuple[str, ...] = ()


def _computed_crc(chunk: PngChunk) -> int:
    return zlib.crc32(chunk.type_bytes + chunk.data) & 0xFFFFFFFF


def _is_critical(chunk_type: str) -> bool:
    return chunk_type[0].isupper()


def _is_safe_to_copy(chunk_type: str) -> bool:
    return chunk_type[3].islower()


def _text_key(chunk: PngChunk) -> str | None:
    if chunk.type == "tEXt" and b"\x00" in chunk.data:
        key = chunk.data.split(b"\x00", 1)[0]
        return key.decode("latin-1") if key else None
    if chunk.type == "zTXt" and b"\x00" in chunk.data:
        key = chunk.data.split(b"\x00", 1)[0]
        return key.decode("latin-1") if key else None
    if chunk.type == "iTXt" and b"\x00" in chunk.data:
        key = chunk.data.split(b"\x00", 1)[0]
        return key.decode("latin-1") if key else None
    return None


def plan_png_cleanup(chunks: list[PngChunk]) -> list[PngCleanupAction]:
    actions: list[PngCleanupAction] = []
    seen_text_keys: set[str] = set()

    metadata = None
    try:
        metadata = extract_png_metadata(chunks)
    except ValueError:
        metadata = None

    for chunk in chunks:
        actual_crc = _computed_crc(chunk)
        if actual_crc != chunk.crc:
            if _is_critical(chunk.type):
                actions.append(PngCleanupAction(chunk.offset, "cannot_remove", chunk.type, "corrupt critical chunk", ("repair source bytes before rewriting",)))
            else:
                actions.append(PngCleanupAction(chunk.offset, "repair_crc", chunk.type, "CRC mismatch", (f"expected={actual_crc:08x}", f"stored={chunk.crc:08x}")))

        key = _text_key(chunk)
        if key is not None:
            if key in seen_text_keys:
                actions.append(PngCleanupAction(chunk.offset, "remove", chunk.type, "duplicate text metadata", (f"key={key}",)))
            else:
                seen_text_keys.add(key)

        if not _is_critical(chunk.type) and not _is_safe_to_copy(chunk.type) and chunk.type not in {"tEXt", "zTXt", "iTXt", "pHYs", "gAMA", "cHRM", "sRGB", "bKGD", "tIME"}:
            actions.append(PngCleanupAction(chunk.offset, "remove", chunk.type, "unsafe unknown ancillary chunk", ()))

        if chunk.type == "PLTE" and metadata is not None and metadata.color_type in {0, 4}:
            actions.append(PngCleanupAction(chunk.offset, "remove", chunk.type, "palette not allowed for grayscale color type", (f"color_type={metadata.color_type}",)))
        if chunk.type == "PLTE" and chunk.length % 3 != 0:
            actions.append(PngCleanupAction(chunk.offset, "normalize_palette", chunk.type, "palette length is not divisible by three", (f"length={chunk.length}",)))

    return sorted(set(actions))
