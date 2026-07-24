# Step 3: Extract deterministic asset metadata

Implement `class PngMetadata` and `extract_png_metadata(chunks: list[PngChunk]) -> PngMetadata`.

The verifier discloses these required behavioral names: ihdr_dimensions_extracted, text_metadata_keys_are_canonical, duplicate_text_uses_canonical_first_value, ztxt_invalid_compression_method_rejected, ztxt_payload_not_inflated_or_decoded, itxt_invalid_compression_method_rejected, invalid_ihdr_compression_rejected, idat_bytes_are_ignored_by_metadata, and read_only_state_check.

Metadata extraction is read-only. It must parse IHDR fields, canonicalize supported tEXt/zTXt/iTXt keys, reject unsupported compression method values with `ValueError`, represent compressed text as `<compressed>`, and never inflate or decode IDAT image data.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_03_smoke.py
```
