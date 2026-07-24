"""Integrated deterministic WebAssembly audit report."""

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


def _parse_problem(exc: Exception) -> WasmProblem:
    return WasmProblem("error", "parse-error", str(exc), -1, 0)


def audit_wasm(data: bytes) -> WasmAuditReport:
    """Run parsing, validation, symbol decoding, and migration planning.

    Malformed section envelopes are recovered as validation-style problems rather
    than escaping from the integrated API. Symbol decoding is attempted only when
    structural validation found no errors, so invalid modules remain auditable.
    """
    try:
        sections_list = parse_wasm_sections(data)
    except (TypeError, ValueError) as exc:
        return WasmAuditReport(sections=(), symbols=(), problems=(_parse_problem(exc),), advice=())
    sections = tuple(sections_list)
    problems_list = validate_wasm_structure(list(sections))
    advice_list = plan_wasm_migration(list(sections))
    symbols_list: list[WasmSymbol] = []
    if not problems_list:
        try:
            symbols_list = summarize_wasm_symbols(list(sections))
        except ValueError as exc:
            problems_list.append(WasmProblem("error", "symbol-decode", str(exc), -1, 0))
            problems_list.sort(key=lambda p: (p.offset, p.code, p.message, p.section_id))
    return WasmAuditReport(
        sections=sections,
        symbols=tuple(symbols_list),
        problems=tuple(problems_list),
        advice=tuple(advice_list),
    )
