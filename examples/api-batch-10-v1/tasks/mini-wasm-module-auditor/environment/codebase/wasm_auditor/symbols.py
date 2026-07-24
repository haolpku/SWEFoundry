"""Starter symbol summarizer."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import WasmSection


@dataclass(frozen=True, slots=True)
class WasmSymbol:
    kind: str
    name: str
    index: int
    descriptor: str
    section: str


def summarize_wasm_symbols(sections: list[WasmSection]) -> list[WasmSymbol]:
    """Return a tiny placeholder summary.

    Step 2 replaces this with restricted decoding for imports, functions,
    globals, memories, and exports.
    """
    result: list[WasmSymbol] = []
    for section in sections:
        if section.id == 7:
            result.append(WasmSymbol("export-section", "exports", 0, f"{len(section.payload)} bytes", section.name))
    return result
