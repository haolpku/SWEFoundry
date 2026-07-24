# Step 1 verification contract

Implement `WasmSection` and `parse_wasm_sections(data: bytes) -> list[WasmSection]` for restricted WebAssembly section envelopes. The verifier is black-box only and discloses these named gates: empty_module_parses, bad_magic_raises, truncated_header_raises, ordered_section_offsets_and_names, truncated_section_payload_raises, truncated_leb_length_raises, leb_u32_overflow_raises, read_only_state_check. Hidden categories disclosed by name: LEB128 overflow, truncation handling, section ordering.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_01_smoke.py
```
