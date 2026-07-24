# Step 1: Parse zone master files

Implement `class DnsRecord` and `parse_zone(text: str, origin: str) -> list[DnsRecord]` for the restricted RFC 1035 master-file subset. The parser must canonicalize domain names case-insensitively to lower-case absolute names, honor `$ORIGIN`, `$TTL`, owner inheritance, SOA/NS/A/AAAA/CNAME/TXT records, sort returned records canonically, and raise `ValueError` for malformed directives or records.

Disclosed verifier checks: origin_relative_names_case_canonicalization, default_ttl_and_owner_inheritance, txt_with_spaces_and_comments, soa_parentheses_numeric_and_names, malformed_directives_raise_valueerror, canonical_sorted_records, origin_directive_and_aaaa_normalization, read_only_state_no_input_change.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run:

`python public_contract_tests/step_01_smoke.py`
