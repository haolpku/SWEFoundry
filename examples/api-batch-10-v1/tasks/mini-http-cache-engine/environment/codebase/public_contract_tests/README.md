Public smoke tests for mini-http-cache-engine.

Run each step_XX_smoke.py from any working directory. Each smoke inserts environment/codebase into sys.path before importing mini_http_cache_engine.

Disclosed behavioral gate names used by black-box verification:
step-1: host_case_normalized, query_order_canonical, vary_header_in_key, method_normalization_head, unsafe_method_rejected, no_store_rejected, vary_star_rejected, header_canonicalization_forms, read_only_inputs.
step-2: max_age_fresh, expired_response_stale, cache_control_over_expires, injected_clock_only, age_header_precedence, stale_if_error_window, unusable_policy_and_status, validators_reported, read_only_entry.
step-3: etag_304_merge, mismatched_etag_raises, mismatched_last_modified_raises, hop_by_hop_not_merged, content_length_not_replaced, validator_preserved_when_absent, allowed_metadata_updated, read_only_entry_and_response.
step-4: post_invalidates_all_variants, purge_key_only, purge_uri_all_variants, no_store_not_retained, affected_keys_sorted, safe_get_noop, unaffected_uri_retained, read_only_entries_and_event.
step-5: fresh_cache_audit, truncated_snapshot_recovery, snapshot_migration_canonical_metadata, duplicate_snapshot_record_recovery, regression_step1_vary_key, regression_step2_max_age_precedence, regression_step3_merge_preserves_body, regression_step4_invalidate_variants, read_only_snapshot_and_events.

Disclosed deterministic mutant names: fp1_ignores_vary, fp2_expires_over_max_age, fp3_drops_body_on_304, fp4_invalidates_only_exact_key, fp5_replays_before_snapshot_validation.
