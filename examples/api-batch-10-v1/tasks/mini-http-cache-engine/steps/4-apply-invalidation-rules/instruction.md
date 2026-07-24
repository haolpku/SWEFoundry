# Step 4 verification contract

Black-box verifier for deterministic offline invalidation. Public API under test: HttpCacheEntry, InvalidationResult and invalidate_http_cache.

Disclosed named checks: post_invalidates_all_variants, purge_key_only, purge_uri_all_variants, no_store_not_retained, affected_keys_sorted, safe_get_noop, unaffected_uri_retained, read_only_entries_and_event.

Deterministic false-positive mutant for this step: fp4_invalidates_only_exact_key.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_04_smoke.py`.
