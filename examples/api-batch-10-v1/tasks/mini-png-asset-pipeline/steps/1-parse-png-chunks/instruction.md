# Step 1: Parse PNG chunks

Implement `class PngChunk` and `parse_png_chunks(data: bytes) -> list[PngChunk]`.

The verifier discloses these required behavioral names: parse_minimal_png_in_file_order, bad_signature_raises_valueerror, truncated_chunk_header_raises, declared_length_past_buffer_is_truncated, missing_iend_raises, trailing_bytes_after_iend_raises, non_letter_chunk_type_rejected, and read_only_state_check.

Parsing is read-only. It must preserve file-order chunks, validate PNG signature, chunk type letters, length bounds, CRC field bounds, IEND termination, and reject trailing bytes after IEND with `ValueError` or a subclass.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_01_smoke.py
```
