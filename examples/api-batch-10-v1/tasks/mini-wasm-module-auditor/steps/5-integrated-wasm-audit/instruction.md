# Step 5 verification contract

Implement `WasmAuditReport` and `audit_wasm(data: bytes)`. The verifier is black-box only and discloses these named gates: valid_module_audit, malformed_parse_recovered_as_problem, invalid_structure_suppresses_symbols, malformed_export_recovery_no_crash, report_and_sections_are_read_only, preserves_migration_advice, regresses_step2_index_spaces, regresses_step3_custom_order, deterministic_repeat_audit. Hidden categories disclosed by name: steps 1-4 regression, binary integrity, exception consistency.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_05_smoke.py
```
