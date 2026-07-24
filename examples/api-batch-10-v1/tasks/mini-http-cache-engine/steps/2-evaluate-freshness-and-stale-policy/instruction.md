# Step 2 verification contract

Black-box verifier for injected-clock freshness and stale policy evaluation. Public API under test: HttpCacheEntry, FreshnessDecision and evaluate_http_freshness.

Disclosed named checks: max_age_fresh, expired_response_stale, cache_control_over_expires, injected_clock_only, age_header_precedence, stale_if_error_window, unusable_policy_and_status, validators_reported, read_only_entry.

Deterministic false-positive mutant for this step: fp2_expires_over_max_age.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_02_smoke.py`.
