# Step 2: Validate zone integrity

Implement `class ZoneProblem` and `validate_zone(records: list[DnsRecord]) -> list[ZoneProblem]`. Validation is read-only and must detect SOA uniqueness/apex placement, apex NS presence, CNAME exclusivity, multiple CNAMEs, duplicate records, and in-bailiwick delegation glue needs. Problems must be sorted by owner, severity rank ERROR/WARNING/INFO, type, and message.

Disclosed verifier checks: healthy_zone_has_no_problems, soa_uniqueness_and_apex, cname_exclusivity_address_conflict, cname_multiple_detected, apex_ns_missing_detected, duplicate_rr_detection, delegation_glue_requirement, severity_owner_type_sorting, read_only_records_input.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run:

`python public_contract_tests/step_02_smoke.py`
