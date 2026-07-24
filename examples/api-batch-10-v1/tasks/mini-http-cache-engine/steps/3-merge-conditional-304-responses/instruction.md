# Step 3 verification contract

Black-box verifier for conditional 304 metadata merge semantics. Public API under test: HttpCacheEntry and merge_http_304.

Disclosed named checks: etag_304_merge, mismatched_etag_raises, mismatched_last_modified_raises, hop_by_hop_not_merged, content_length_not_replaced, validator_preserved_when_absent, allowed_metadata_updated, read_only_entry_and_response.

Deterministic false-positive mutant for this step: fp3_drops_body_on_304.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_03_smoke.py`.
