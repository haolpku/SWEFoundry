# Step 3: Simulate offline DNS answers

Implement `class DnsAnswer` and `answer_zone(records: list[DnsRecord], qname: str, qtype: str) -> DnsAnswer`. The resolver must be deterministic, offline, and socket-free; canonicalize qnames, support SOA/NS/A/AAAA/CNAME/TXT, return NOERROR/NXDOMAIN/CNAME_LOOP, follow bounded CNAME chains, sort answers, and leave inputs untouched.

Disclosed verifier checks: direct_a_record_answer, cname_chain_answer_order, nxdomain_for_absent_owner, noerror_nodata_existing_owner, bounded_cname_loop_detection, unsupported_query_type_valueerror, answer_sorting_for_rrset, qname_case_canonicalization, read_only_records_input.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run:

`python public_contract_tests/step_03_smoke.py`
