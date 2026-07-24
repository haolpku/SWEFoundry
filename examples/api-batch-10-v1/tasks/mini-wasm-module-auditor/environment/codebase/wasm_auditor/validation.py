"""Starter structural validation."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import WasmSection


@dataclass(frozen=True, slots=True)
class WasmProblem:
    severity: str
    code: str
    message: str
    section_id: int
    offset: int


def validate_wasm_structure(sections: list[WasmSection]) -> list[WasmProblem]:
    """Return duplicate singleton-section problems only.

    Step 3 replaces this with complete read-only structural validation.
    """
    seen: set[int] = set()
    problems: list[WasmProblem] = []
    for section in sections:
        if section.id != 0 and section.id in seen:
            problems.append(WasmProblem("error", "duplicate-section", f"duplicate {section.name} section", section.id, section.offset))
        seen.add(section.id)
    return sorted(problems, key=lambda p: (p.offset, p.code, p.message))
