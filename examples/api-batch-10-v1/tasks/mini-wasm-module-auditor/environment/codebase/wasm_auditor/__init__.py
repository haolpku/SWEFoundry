"""Educational offline WebAssembly module auditor starter package."""

from .parser import WasmSection, parse_wasm_sections
from .symbols import WasmSymbol, summarize_wasm_symbols
from .validation import WasmProblem, validate_wasm_structure
from .migration import WasmMigrationAdvice, plan_wasm_migration
from .audit import WasmAuditReport, audit_wasm
from .exceptions import WasmAuditError, WasmFormatError

__all__ = [
    "WasmSection",
    "parse_wasm_sections",
    "WasmSymbol",
    "summarize_wasm_symbols",
    "WasmProblem",
    "validate_wasm_structure",
    "WasmMigrationAdvice",
    "plan_wasm_migration",
    "WasmAuditReport",
    "audit_wasm",
    "WasmAuditError",
    "WasmFormatError",
]
