#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from verifier.common import finalize, get_context, run_case

workspace, tests_dir, reward_dir = get_context('step-3')
checks = []
base = """
from dns_zone_auditor import DnsRecord, answer_zone
records = [
    DnsRecord('www.example.com.', 'A', 300, ('192.0.2.10',)),
    DnsRecord('www.example.com.', 'TXT', 300, ('hello',)),
    DnsRecord('alias.example.com.', 'CNAME', 300, ('www.example.com.',)),
    DnsRecord('chain.example.com.', 'CNAME', 300, ('alias.example.com.',)),
]
"""
checks.append(run_case('direct_a_record_answer', base + r'''
ans = answer_zone(records, 'www.example.com', 'A')
assert ans.qname == 'www.example.com.'
assert ans.qtype == 'A'
assert ans.rcode == 'NOERROR'
assert ans.answers == (DnsRecord('www.example.com.', 'A', 300, ('192.0.2.10',)),)
assert ans.chain == ('www.example.com.',)
''', workspace))
checks.append(run_case('cname_chain_answer_order', base + r'''
ans = answer_zone(records, 'chain.example.com.', 'A')
assert ans.rcode == 'NOERROR'
assert [r.type for r in ans.answers] == ['CNAME', 'CNAME', 'A']
assert ans.chain == ('chain.example.com.', 'alias.example.com.', 'www.example.com.')
''', workspace))
checks.append(run_case('nxdomain_for_absent_owner', base + r'''
ans = answer_zone(records, 'missing.example.com', 'A')
assert ans.rcode == 'NXDOMAIN'
assert ans.answers == ()
assert ans.chain == ('missing.example.com.',)
''', workspace))
checks.append(run_case('noerror_nodata_existing_owner', base + r'''
ans = answer_zone(records, 'www.example.com', 'AAAA')
assert ans.rcode == 'NOERROR'
assert ans.answers == ()
assert ans.chain == ('www.example.com.',)
''', workspace))
checks.append(run_case('bounded_cname_loop_detection', r'''
from dns_zone_auditor import DnsRecord, answer_zone
records = [DnsRecord('a.example.com.', 'CNAME', 60, ('b.example.com.',)), DnsRecord('b.example.com.', 'CNAME', 60, ('a.example.com.',))]
ans = answer_zone(records, 'a.example.com', 'A')
assert ans.rcode == 'CNAME_LOOP'
assert ans.chain[0] == 'a.example.com.'
assert len(ans.chain) <= 5
''', workspace, timeout=3))
checks.append(run_case('unsupported_query_type_valueerror', base + r'''
try:
    answer_zone(records, 'www.example.com', 'MX')
except ValueError:
    pass
else:
    raise AssertionError('unsupported query type must raise ValueError')
''', workspace))
checks.append(run_case('answer_sorting_for_rrset', r'''
from dns_zone_auditor import DnsRecord, answer_zone
records = [DnsRecord('multi.example.com.', 'A', 500, ('192.0.2.2',)), DnsRecord('multi.example.com.', 'A', 100, ('192.0.2.1',))]
ans = answer_zone(records, 'multi.example.com', 'A')
assert [(r.data, r.ttl) for r in ans.answers] == [(('192.0.2.1',), 100), (('192.0.2.2',), 500)]
''', workspace))
checks.append(run_case('qname_case_canonicalization', base + r'''
ans = answer_zone(records, 'WWW.Example.COM', 'txt')
assert ans.qname == 'www.example.com.'
assert ans.qtype == 'TXT'
assert ans.rcode == 'NOERROR'
''', workspace))
checks.append(run_case('read_only_records_input', base + r'''
before = list(records)
answer_zone(records, 'alias.example.com', 'A')
assert records == before
''', workspace))
raise SystemExit(0 if finalize('step-3', checks, reward_dir) else 1)
