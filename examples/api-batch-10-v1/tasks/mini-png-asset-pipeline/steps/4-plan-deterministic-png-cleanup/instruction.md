# Step 4: Plan deterministic PNG cleanup

Implement `class PngCleanupAction` and `plan_png_cleanup(chunks: list[PngChunk]) -> list[PngCleanupAction]`.

The verifier discloses these required behavioral names: duplicate_text_removal_planned, clean_png_empty_plan, corrupt_ancillary_crc_repair_planned, corrupt_critical_chunk_not_removed, unsafe_unknown_ancillary_removed, grayscale_palette_removal_planned, bad_palette_length_normalized, plan_is_idempotent_and_sorted, and read_only_state_check.

Cleanup planning is read-only. It must produce deterministic idempotent actions for duplicate metadata, ancillary CRC repair, unsafe ancillary removal, PLTE normalization/removal, and must never plan to remove corrupt critical chunks.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_04_smoke.py
```
