"""Starter parser for WebAssembly section envelopes."""

from __future__ import annotations

from dataclasses import dataclass

from .leb128 import read_u32_leb

_MAGIC = b"\x00asm"
_VERSION = b"\x01\x00\x00\x00"


@dataclass(frozen=True, slots=True)
class WasmSection:
    id: int
    name: str
    payload: bytes
    offset: int
    size: int


_SECTION_NAMES = {
    0: "custom",
    1: "type",
    2: "import",
    3: "function",
    4: "table",
    5: "memory",
    6: "global",
    7: "export",
    8: "start",
    9: "element",
    10: "code",
    11: "data",
    12: "data_count",
}


def parse_wasm_sections(data: bytes) -> list[WasmSection]:
    """Parse section envelopes from a wasm binary.

    Starter behavior validates the header but is deliberately too permissive for
    truncated payloads; step 1 installs the complete parser.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    raw = bytes(data)
    if len(raw) < 8:
        raise ValueError("truncated wasm header")
    if raw[:4] != _MAGIC:
        raise ValueError("bad wasm magic")
    if raw[4:8] != _VERSION:
        raise ValueError("unsupported wasm version")
    sections: list[WasmSection] = []
    pos = 8
    while pos < len(raw):
        section_offset = pos
        section_id = raw[pos]
        pos += 1
        size, pos = read_u32_leb(raw, pos)
        payload = raw[pos:pos + size]
        pos += size
        sections.append(WasmSection(section_id, _SECTION_NAMES.get(section_id, f"unknown-{section_id}"), payload, section_offset, size))
    return sections
