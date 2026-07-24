"""Starter migration advice."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import WasmSection


@dataclass(frozen=True, slots=True)
class WasmMigrationAdvice:
    category: str
    target: str
    message: str


def plan_wasm_migration(sections: list[WasmSection]) -> list[WasmMigrationAdvice]:
    """Return no advice in the starter package.

    Step 4 installs deterministic compatibility planning.
    """
    return []
