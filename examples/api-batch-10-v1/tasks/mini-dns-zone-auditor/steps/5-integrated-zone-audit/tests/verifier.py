#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from verifier.common import finalize, get_context, run_case

workspace, tests_dir, reward_dir = get_context('step-5')
checks = []
healthy = "$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\n@ IN NS ns\nns IN A 192.0.2.53\nwww IN A 192.0.2.10\nalias IN CNAME www\n"
checks.append(run_case('healthy_zone_audit_preserves_outputs', r'''
from dns_zone_auditor import audit_zone
text = '$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\n@ IN NS ns\nns IN A 192.0.2.53\nwww IN A 192.0.2.10\nalias IN CNAME www\n'
report = audit_zone(text, 'Example.COM', [('alias.example.com', 'A'), ('www.example.com.', 'TXT')], 300)
assert report.origin == 'example.com.'
assert report.problems == ()
assert len(report.records) == 5
assert len(report.answers) == 2
assert report.answers[0].rcode == 'NOERROR'
assert [r.type for r in report.answers[0].answers] == ['CNAME', 'A']
assert report.migration.records[0].owner == 'alias.example.com.'
assert report.recovery['record_count'] == '5'
''', workspace))
checks.append(run_case('broken_zone_audit_still_answers_queries', r'''
from dns_zone_auditor import audit_zone
text = '$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\nbad IN CNAME www\nbad IN A 192.0.2.9\n'
report = audit_zone(text, 'example.com', [('bad.example.com', 'A')], 300)
assert report.problems
assert len(report.answers) == 1
assert report.answers[0].qname == 'bad.example.com.'
assert report.answers[0].rcode == 'NOERROR'
assert report.recovery['problem_count'] == str(len(report.problems))
assert report.recovery['answer_count'] == '1'
''', workspace))
checks.append(run_case('recovery_fields_and_sha256_exact', r'''
import hashlib
from dns_zone_auditor import audit_zone
text = '$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\n@ IN NS ns\nns IN A 192.0.2.53\nwww IN A 192.0.2.10\n'
report = audit_zone(text, 'example.com', [('www.example.com', 'A')], 300)
def record_line(r):
    return '|'.join((r.owner, r.type, str(r.ttl), *r.data))
def answer_line(a):
    rr = ';'.join(record_line(r) for r in a.answers)
    chain = '>'.join(a.chain)
    return '|'.join((a.qname, a.qtype, a.rcode, chain, rr))
def sha(lines):
    return hashlib.sha256(('\n'.join(lines) + '\n').encode('utf-8')).hexdigest()
assert set(report.recovery) == {'origin', 'record_count', 'problem_count', 'answer_count', 'records_sha256', 'problems_sha256', 'answers_sha256'}
assert report.recovery['records_sha256'] == sha([record_line(r) for r in report.records])
assert report.recovery['answers_sha256'] == sha([answer_line(a) for a in report.answers])
''', workspace))
checks.append(run_case('canonical_report_ordering', r'''
from dns_zone_auditor import audit_zone
text = '$TTL 300\nWWW IN A 192.0.2.2\n@ IN SOA Ns HostMaster 1 7200 3600 1209600 300\n@ IN NS Ns\nAlias IN CNAME WWW\nAlias IN TXT bad\n'
report = audit_zone(text, 'Example.COM', [('WWW.EXAMPLE.COM', 'A')], 300)
record_keys = [(r.owner, r.type, r.data, r.ttl) for r in report.records]
assert record_keys == sorted(record_keys)
problem_keys = [(p.owner, p.severity, p.type, p.message) for p in report.problems]
assert problem_keys == sorted(problem_keys, key=lambda x: (x[0], {'ERROR': 0, 'WARNING': 1, 'INFO': 2}.get(x[1], 9), x[2], x[3]))
assert report.answers[0].qname == 'www.example.com.'
''', workspace))
checks.append(run_case('step1_parser_regression', r'''
from dns_zone_auditor import parse_zone
records = parse_zone('$TTL 90\nMiXeD IN TXT "hello there"\n  IN A 192.0.2.5\n', 'Example.COM')
assert [r.owner for r in records] == ['mixed.example.com.', 'mixed.example.com.']
assert {r.ttl for r in records} == {90}
assert any(r.data == ('hello there',) for r in records)
''', workspace))
checks.append(run_case('step2_validation_regression', r'''
from dns_zone_auditor import DnsRecord, validate_zone
soa = DnsRecord('example.com.', 'SOA', 300, ('ns.example.com.', 'hostmaster.example.com.', '1', '7200', '3600', '1209600', '300'))
records = [soa, DnsRecord('example.com.', 'NS', 300, ('ns.example.com.',)), DnsRecord('alias.example.com.', 'CNAME', 300, ('x.example.com.',)), DnsRecord('alias.example.com.', 'A', 300, ('192.0.2.8',)), DnsRecord('child.example.com.', 'NS', 300, ('ns.child.example.com.',))]
types = {p.type for p in validate_zone(records)}
assert {'CNAME_EXCLUSIVE', 'GLUE_MISSING'} <= types
''', workspace))
checks.append(run_case('step3_resolver_regression', r'''
from dns_zone_auditor import DnsRecord, answer_zone
records = [DnsRecord('a.example.com.', 'CNAME', 60, ('b.example.com.',)), DnsRecord('b.example.com.', 'CNAME', 60, ('a.example.com.',))]
ans = answer_zone(records, 'a.example.com', 'A')
assert ans.rcode == 'CNAME_LOOP'
''', workspace, timeout=3))
checks.append(run_case('step4_migration_regression', r'''
import hashlib
from dns_zone_auditor import DnsRecord, plan_zone_migration
records = [DnsRecord('multi.example.com.', 'A', 100, ('192.0.2.2',)), DnsRecord('multi.example.com.', 'A', 100, ('192.0.2.1',))]
plan = plan_zone_migration(records, 30)
expected = hashlib.sha256('multi.example.com.|A|30|192.0.2.1\nmulti.example.com.|A|30|192.0.2.2'.encode('utf-8')).hexdigest()
assert plan.digests['multi.example.com. A'] == expected
assert records[0].ttl == 100
''', workspace))
checks.append(run_case('read_only_inputs_and_recovery_mapping', r'''
from dns_zone_auditor import audit_zone
text = '$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\n@ IN NS ns\nns IN A 192.0.2.53\nwww IN A 192.0.2.10\n'
origin = 'Example.COM'
queries = [('www.example.com', 'A')]
before = (text, origin, list(queries))
report = audit_zone(text, origin, queries, 300)
assert (text, origin, queries) == before
try:
    report.recovery['x'] = 'y'
except TypeError:
    pass
else:
    raise AssertionError('recovery mapping must be read-only')
''', workspace))
raise SystemExit(0 if finalize('step-5', checks, reward_dir) else 1)
