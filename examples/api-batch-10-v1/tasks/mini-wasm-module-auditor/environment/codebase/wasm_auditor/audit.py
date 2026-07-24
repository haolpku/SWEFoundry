"""Starter integrated audit API."""

from __future__ import annotations

from dataclasses import dataclass

from .migration import WasmMigrationAdvice, plan_wasm_migration
from .parser import WasmSection, parse_wasm_sections
from .symbols import WasmSymbol, summarize_wasm_symbols
from .validation import WasmProblem, validate_wasm_structure


@dataclass(frozen=True, slots=True)
class WasmAuditReport:
    sections: tuple[WasmSection, ...]
    symbols: tuple[WasmSymbol, ...]
    problems: tuple[WasmProblem, ...]
    advice: tuple[WasmMigrationAdvice, ...]


def audit_wasm(data: bytes) -> WasmAuditReport:
    sections = tuple(parse_wasm_sections(data))
    return WasmAuditReport(
        sections=sections,
        symbols=tuple(summarize_wasm_symbols(list(sections))),
        problems=tuple(validate_wasm_structure(list(sections))),
        advice=tuple(plan_wasm_migration(list(sections))),
    )
