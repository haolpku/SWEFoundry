# Step 3 verification contract

Implement `WasmProblem` and `validate_wasm_structure(sections)`. The verifier is black-box only and discloses these named gates: duplicate_type_section_reported, export_index_out_of_bounds_reported, custom_sections_do_not_break_order, core_out_of_order_reported, function_code_count_mismatch_reported, deterministic_problem_sorting, malformed_import_reported_not_raised, read_only_state_check. Hidden categories disclosed by name: singleton enforcement, cross-section counts, custom section placement.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_03_smoke.py
```
