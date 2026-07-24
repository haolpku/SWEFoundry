"""Read-only WebAssembly structural validation."""

from __future__ import annotations

from dataclasses import dataclass

from .leb128 import read_name, read_u32_leb
from .parser import WasmSection

_KIND = {0: "function", 1: "table", 2: "memory", 3: "global"}


@dataclass(frozen=True, slots=True)
class WasmProblem:
    severity: str
    code: str
    message: str
    section_id: int
    offset: int


def _problem(code: str, message: str, section: WasmSection) -> WasmProblem:
    return WasmProblem("error", code, message, section.id, section.offset)


def _read_byte(data: bytes, pos: int, end: int) -> tuple[int, int]:
    if pos >= end:
        raise ValueError("truncated section field")
    return data[pos], pos + 1


def _skip_limits(data: bytes, pos: int, end: int) -> int:
    flag, pos = _read_byte(data, pos, end)
    if flag not in (0, 1):
        raise ValueError("invalid limits flag")
    _minimum, pos = read_u32_leb(data, pos, end)
    if flag == 1:
        _maximum, pos = read_u32_leb(data, pos, end)
    return pos


def _skip_table_type(data: bytes, pos: int, end: int) -> int:
    _elem, pos = _read_byte(data, pos, end)
    return _skip_limits(data, pos, end)


def _skip_global_type(data: bytes, pos: int, end: int) -> int:
    _valtype, pos = _read_byte(data, pos, end)
    _mut, pos = _read_byte(data, pos, end)
    return pos


def _decode_import_counts(section: WasmSection) -> dict[str, int]:
    data = section.payload
    end = len(data)
    pos = 0
    count, pos = read_u32_leb(data, pos, end)
    counts = {"function": 0, "table": 0, "memory": 0, "global": 0}
    for _ in range(count):
        _module, pos = read_name(data, pos, end)
        _field, pos = read_name(data, pos, end)
        kind_byte, pos = _read_byte(data, pos, end)
        kind = _KIND.get(kind_byte)
        if kind is None:
            raise ValueError("unsupported import kind")
        counts[kind] += 1
        if kind == "function":
            _type, pos = read_u32_leb(data, pos, end)
        elif kind == "table":
            pos = _skip_table_type(data, pos, end)
        elif kind == "memory":
            pos = _skip_limits(data, pos, end)
        else:
            pos = _skip_global_type(data, pos, end)
    if pos != end:
        raise ValueError("trailing import bytes")
    return counts


def _vector_count(section: WasmSection) -> int:
    count, _pos = read_u32_leb(section.payload, 0, len(section.payload))
    return count


def _export_entries(section: WasmSection) -> list[tuple[str, int, int]]:
    data = section.payload
    end = len(data)
    pos = 0
    count, pos = read_u32_leb(data, pos, end)
    result: list[tuple[str, int, int]] = []
    for _ in range(count):
        name, pos = read_name(data, pos, end)
        kind, pos = _read_byte(data, pos, end)
        index, pos = read_u32_leb(data, pos, end)
        result.append((name, kind, index))
    if pos != end:
        raise ValueError("trailing export bytes")
    return result


def validate_wasm_structure(sections: list[WasmSection]) -> list[WasmProblem]:
    """Validate section order, singleton duplication, counts, and export bounds."""
    problems: list[WasmProblem] = []
    seen: set[int] = set()
    last_core = 0
    import_counts = {"function": 0, "table": 0, "memory": 0, "global": 0}
    defined_counts = {"function": 0, "table": 0, "memory": 0, "global": 0, "code": 0}
    export_sections: list[WasmSection] = []
    for section in sections:
        if section.id == 0:
            continue
        if section.id in seen:
            problems.append(_problem("duplicate-section", f"duplicate {section.name} section", section))
        seen.add(section.id)
        if section.id < last_core:
            problems.append(_problem("section-order", f"{section.name} section appears out of order", section))
        else:
            last_core = section.id
        try:
            if section.id == 2:
                import_counts = _decode_import_counts(section)
            elif section.id == 3:
                defined_counts["function"] = _vector_count(section)
            elif section.id == 4:
                defined_counts["table"] = _vector_count(section)
            elif section.id == 5:
                defined_counts["memory"] = _vector_count(section)
            elif section.id == 6:
                defined_counts["global"] = _vector_count(section)
            elif section.id == 7:
                export_sections.append(section)
            elif section.id == 10:
                defined_counts["code"] = _vector_count(section)
        except ValueError as exc:
            problems.append(_problem("malformed-section", str(exc), section))
    if defined_counts["function"] != defined_counts["code"]:
        section = next((s for s in sections if s.id in (3, 10)), sections[0] if sections else WasmSection(-1, "module", b"", 0, 0))
        problems.append(WasmProblem("error", "function-code-count", "function and code section counts differ", section.id, section.offset))
    totals = {
        "function": import_counts["function"] + defined_counts["function"],
        "table": import_counts["table"] + defined_counts["table"],
        "memory": import_counts["memory"] + defined_counts["memory"],
        "global": import_counts["global"] + defined_counts["global"],
    }
    for section in export_sections:
        try:
            for name, kind_byte, index in _export_entries(section):
                kind = _KIND.get(kind_byte)
                if kind is None:
                    problems.append(_problem("export-kind", f"export {name!r} has unsupported kind {kind_byte}", section))
                elif index >= totals[kind]:
                    problems.append(_problem("export-index", f"export {name!r} references {kind} index {index} but only {totals[kind]} exist", section))
        except ValueError as exc:
            problems.append(_problem("malformed-section", str(exc), section))
    return sorted(problems, key=lambda p: (p.offset, p.code, p.message, p.section_id))
