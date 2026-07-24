# Step 2 verification contract

Implement `WasmSymbol` and `summarize_wasm_symbols(sections)`. The verifier is black-box only and discloses these named gates: exported_function_summary, invalid_utf8_import_name_raises, separate_index_spaces_for_imports, defined_function_index_after_import, deterministic_symbol_order, export_memory_kind_descriptor, trailing_export_bytes_raise, read_only_state_check. Hidden categories disclosed by name: index space accounting, UTF-8 validation, symbol ordering.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_02_smoke.py
```
