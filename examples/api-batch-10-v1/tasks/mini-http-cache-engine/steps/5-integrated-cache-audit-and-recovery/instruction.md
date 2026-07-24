# Step 5 verification contract

Black-box verifier for integrated cache audit, migration and disk snapshot recovery. Public API under test: HttpCacheAuditReport and audit_http_cache, with critical regressions for build_cache_key, evaluate_http_freshness, merge_http_304 and invalidate_http_cache.

Disclosed named checks: fresh_cache_audit, truncated_snapshot_recovery, snapshot_migration_canonical_metadata, duplicate_snapshot_record_recovery, regression_step1_vary_key, regression_step2_max_age_precedence, regression_step3_merge_preserves_body, regression_step4_invalidate_variants, read_only_snapshot_and_events.

Deterministic false-positive mutant for this step: fp5_replays_before_snapshot_validation.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_05_smoke.py`.
