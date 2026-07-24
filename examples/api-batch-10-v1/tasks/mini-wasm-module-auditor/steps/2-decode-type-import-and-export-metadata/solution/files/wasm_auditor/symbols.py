"""Restricted deterministic WebAssembly symbol decoding."""

from __future__ import annotations

from dataclasses import dataclass

from .leb128 import read_name, read_u32_leb
from .parser import WasmSection

_KIND = {0: "function", 1: "table", 2: "memory", 3: "global"}


@dataclass(frozen=True, slots=True)
class WasmSymbol:
    kind: str
    name: str
    index: int
    descriptor: str
    section: str


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
    elem, pos = _read_byte(data, pos, end)
    if elem not in (0x70, 0x6F):
        raise ValueError("unsupported table element type")
    return _skip_limits(data, pos, end)


def _skip_global_type(data: bytes, pos: int, end: int) -> int:
    valtype, pos = _read_byte(data, pos, end)
    if valtype not in (0x7F, 0x7E, 0x7D, 0x7C, 0x70, 0x6F):
        raise ValueError("unsupported global value type")
    mut, pos = _read_byte(data, pos, end)
    if mut not in (0, 1):
        raise ValueError("invalid global mutability")
    return pos


def _decode_imports(section: WasmSection) -> tuple[list[WasmSymbol], dict[str, int]]:
    data = section.payload
    end = len(data)
    pos = 0
    count, pos = read_u32_leb(data, pos, end)
    indexes = {"function": 0, "table": 0, "memory": 0, "global": 0}
    symbols: list[WasmSymbol] = []
    for _ in range(count):
        module, pos = read_name(data, pos, end)
        field, pos = read_name(data, pos, end)
        kind_byte, pos = _read_byte(data, pos, end)
        kind = _KIND.get(kind_byte)
        if kind is None:
            raise ValueError("unsupported import kind")
        index = indexes[kind]
        indexes[kind] += 1
        if kind == "function":
            type_index, pos = read_u32_leb(data, pos, end)
            descriptor = f"import {module}.{field} type_index={type_index}"
        elif kind == "table":
            pos = _skip_table_type(data, pos, end)
            descriptor = f"import {module}.{field} table"
        elif kind == "memory":
            pos = _skip_limits(data, pos, end)
            descriptor = f"import {module}.{field} memory"
        else:
            pos = _skip_global_type(data, pos, end)
            descriptor = f"import {module}.{field} global"
        symbols.append(WasmSymbol(kind, f"{module}.{field}", index, descriptor, section.name))
    if pos != end:
        raise ValueError("trailing import section bytes")
    return symbols, indexes


def _function_type_indices(section: WasmSection) -> list[int]:
    data = section.payload
    end = len(data)
    pos = 0
    count, pos = read_u32_leb(data, pos, end)
    result: list[int] = []
    for _ in range(count):
        type_index, pos = read_u32_leb(data, pos, end)
        result.append(type_index)
    if pos != end:
        raise ValueError("trailing function section bytes")
    return result


def _count_section(section: WasmSection) -> int:
    data = section.payload
    if not data:
        raise ValueError("truncated vector")
    count, _pos = read_u32_leb(data, 0, len(data))
    return count


def summarize_wasm_symbols(sections: list[WasmSection]) -> list[WasmSymbol]:
    """Decode imports, declared functions, memories, globals, and exports."""
    symbols: list[WasmSymbol] = []
    indexes = {"function": 0, "table": 0, "memory": 0, "global": 0}
    function_types: list[int] = []
    for section in sections:
        if section.id == 2:
            imported, indexes = _decode_imports(section)
            symbols.extend(imported)
        elif section.id == 3:
            function_types = _function_type_indices(section)
            for local, type_index in enumerate(function_types):
                index = indexes["function"] + local
                symbols.append(WasmSymbol("function", f"function[{index}]", index, f"defined type_index={type_index}", section.name))
        elif section.id == 5:
            count = _count_section(section)
            for local in range(count):
                index = indexes["memory"] + local
                symbols.append(WasmSymbol("memory", f"memory[{index}]", index, "defined memory", section.name))
        elif section.id == 6:
            count = _count_section(section)
            for local in range(count):
                index = indexes["global"] + local
                symbols.append(WasmSymbol("global", f"global[{index}]", index, "defined global", section.name))
    for section in sections:
        if section.id != 7:
            continue
        data = section.payload
        end = len(data)
        pos = 0
        count, pos = read_u32_leb(data, pos, end)
        for _ in range(count):
            name, pos = read_name(data, pos, end)
            kind_byte, pos = _read_byte(data, pos, end)
            index, pos = read_u32_leb(data, pos, end)
            kind = _KIND.get(kind_byte, f"kind-{kind_byte}")
            symbols.append(WasmSymbol(f"export-{kind}", name, index, f"export {kind} index={index}", section.name))
        if pos != end:
            raise ValueError("trailing export section bytes")
    return symbols
