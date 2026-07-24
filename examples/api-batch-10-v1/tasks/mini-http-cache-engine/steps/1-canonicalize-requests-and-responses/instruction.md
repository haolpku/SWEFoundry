# Step 1 verification contract

Black-box verifier for canonical request and response parsing. Public API under test: HttpCacheEntry and build_cache_key.

Disclosed named checks: host_case_normalized, query_order_canonical, vary_header_in_key, method_normalization_head, unsafe_method_rejected, no_store_rejected, vary_star_rejected, header_canonicalization_forms, read_only_inputs.

Deterministic false-positive mutant for this step: fp1_ignores_vary.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_01_smoke.py`.
