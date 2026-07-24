# Step 4 verification contract

Implement `WasmMigrationAdvice` and `plan_wasm_migration(sections)`. The verifier is black-box only and discloses these named gates: unknown_custom_section_advice, canonical_name_section_advice, unsupported_start_feature_advice, deprecated_export_name_advice, deduplicates_equivalent_advice, stable_advice_ordering, malformed_custom_recovery_advice, read_only_state_check. Hidden categories disclosed by name: feature detection, advice deduplication, stable ordering.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_04_smoke.py
```
