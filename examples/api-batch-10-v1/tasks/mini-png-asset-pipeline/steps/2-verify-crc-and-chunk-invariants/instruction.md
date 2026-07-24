# Step 2: Verify CRC and chunk invariants

Implement `class PngProblem` and `validate_png_chunks(chunks: list[PngChunk]) -> list[PngProblem]`.

The verifier discloses these required behavioral names: ancillary_crc_mismatch_reported, critical_crc_mismatch_reported, idat_before_ihdr_reported, singleton_chunk_violations_reported, plte_after_idat_reported, nonconsecutive_idat_reported, problems_sorted_by_offset_and_code, and read_only_state_check.

Validation is read-only and must report CRC32 mismatches for critical and ancillary chunks, IHDR/PLTE/IEND singleton and ordering constraints, IDAT ordering and consecutiveness, and deterministic sorting by offset and diagnostic code.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_02_smoke.py
```
