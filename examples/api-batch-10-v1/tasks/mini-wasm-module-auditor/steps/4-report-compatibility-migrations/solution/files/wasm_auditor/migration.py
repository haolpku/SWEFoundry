"""Deterministic read-only WebAssembly migration advice."""

from __future__ import annotations

from dataclasses import dataclass

from .leb128 import read_name
from .parser import WasmSection

_KNOWN_CUSTOM = {"name", "producers", "target_features"}
_FEATURE_SECTIONS = {8: "start", 9: "element", 11: "data", 12: "data_count"}


@dataclass(frozen=True, slots=True)
class WasmMigrationAdvice:
    category: str
    target: str
    message: str


def _custom_name(section: WasmSection) -> str:
    if section.id != 0:
        return ""
    name, _pos = read_name(section.payload, 0, len(section.payload))
    return name


def _export_names(section: WasmSection) -> list[str]:
    from .symbols import _read_byte
    from .leb128 import read_u32_leb
    data = section.payload
    end = len(data)
    pos = 0
    count, pos = read_u32_leb(data, pos, end)
    names: list[str] = []
    for _ in range(count):
        name, pos = read_name(data, pos, end)
        _kind, pos = _read_byte(data, pos, end)
        _index, pos = read_u32_leb(data, pos, end)
        names.append(name)
    return names


def plan_wasm_migration(sections: list[WasmSection]) -> list[WasmMigrationAdvice]:
    """Return stable compatibility advice without mutating section payloads."""
    advice: set[WasmMigrationAdvice] = set()
    custom_seen: list[tuple[str, int]] = []
    for section in sections:
        if section.id in _FEATURE_SECTIONS:
            target = _FEATURE_SECTIONS[section.id]
            advice.add(WasmMigrationAdvice("unsupported-feature", target, f"review use of {target} section for restricted runtimes"))
        if section.id == 0:
            try:
                name = _custom_name(section)
            except ValueError:
                advice.add(WasmMigrationAdvice("malformed-custom", "custom", "custom section name is not decodable"))
                continue
            custom_seen.append((name, section.offset))
            if name not in _KNOWN_CUSTOM:
                advice.add(WasmMigrationAdvice("unknown-custom-section", name, f"preserve or strip unknown custom section {name!r} explicitly"))
        elif section.id == 7:
            try:
                for name in _export_names(section):
                    if name.startswith("old_") or "__" in name:
                        advice.add(WasmMigrationAdvice("deprecated-name", name, f"rename deprecated export {name!r} before migration"))
            except ValueError:
                advice.add(WasmMigrationAdvice("malformed-export", "export", "export names could not be decoded for migration planning"))
    if custom_seen:
        canonical = sorted(custom_seen, key=lambda item: (item[0].encode("utf-8"), item[1]))
        if custom_seen != canonical:
            advice.add(WasmMigrationAdvice("canonical-custom-order", "custom", "order custom sections canonically by UTF-8 name for reproducible builds"))
        name_offsets = [offset for name, offset in custom_seen if name == "name"]
        if name_offsets and name_offsets[0] != min(offset for _name, offset in custom_seen):
            advice.add(WasmMigrationAdvice("canonical-name-section", "name", "place the name custom section before other custom sections"))
    return sorted(advice, key=lambda item: (item.category, item.target, item.message))
