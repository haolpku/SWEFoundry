# Step 5: Integrated zone audit

Implement `class ZoneAuditReport` and `audit_zone(text: str, origin: str, queries: list[tuple[str, str]], target_ttl: int) -> ZoneAuditReport`. The integrated audit must preserve Steps 1-4 behavior, always simulate requested offline queries even when validation problems exist, return deterministic ordered records/problems/answers/migration, and provide immutable replayable recovery metadata including sha256 digests.

Disclosed verifier checks: healthy_zone_audit_preserves_outputs, broken_zone_audit_still_answers_queries, recovery_fields_and_sha256_exact, canonical_report_ordering, step1_parser_regression, step2_validation_regression, step3_resolver_regression, step4_migration_regression, read_only_inputs_and_recovery_mapping.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run:

`python public_contract_tests/step_05_smoke.py`
