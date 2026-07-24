# Step 4: Plan serial and digest migration

Implement `class ZoneMigration` and `plan_zone_migration(records: list[DnsRecord], target_ttl: int) -> ZoneMigration`. The planner must be deterministic and read-only: validate non-negative target TTLs, canonicalize record order, increment SOA serials, normalize TTLs, report stable changes, and compute sha256 digests from canonical DNS order rather than input order.

Disclosed verifier checks: soa_serial_increment_planned, ttl_normalization_all_records, digest_canonical_order_independent, already_normalized_without_soa_empty_changes, digests_are_read_only, negative_target_ttl_valueerror, migration_records_canonical_order, read_only_records_input.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run:

`python public_contract_tests/step_04_smoke.py`
