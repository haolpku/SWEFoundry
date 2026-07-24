# Public API contract

Package: `wasm_auditor`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-read-wasm-binary-sections

Public API:
- `class WasmSection:`
- `def parse_wasm_sections(data: bytes) -> list[WasmSection]`

Public behavior cases:
- `empty-module-parses`
- `bad-magic-raises`

## Step 2: 2-decode-type-import-and-export-metadata

Public API:
- `class WasmSymbol:`
- `def summarize_wasm_symbols(sections: list[WasmSection]) -> list[WasmSymbol]`

Public behavior cases:
- `exported-function-summary`
- `invalid-name-raises`

## Step 3: 3-validate-structural-integrity

Public API:
- `class WasmProblem:`
- `def validate_wasm_structure(sections: list[WasmSection]) -> list[WasmProblem]`

Public behavior cases:
- `duplicate-type-section-reported`
- `export-index-out-of-bounds`

## Step 4: 4-report-compatibility-migrations

Public API:
- `class WasmMigrationAdvice:`
- `def plan_wasm_migration(sections: list[WasmSection]) -> list[WasmMigrationAdvice]`

Public behavior cases:
- `unknown-custom-section-advice`
- `canonical-name-section-advice`

## Step 5: 5-integrated-wasm-audit

Public API:
- `class WasmAuditReport:`
- `def audit_wasm(data: bytes) -> WasmAuditReport`

Public behavior cases:
- `valid-module-audit`
- `invalid-module-audit-problems`
