#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from verifier.common import finalize, get_context, run_case

workspace, tests_dir, reward_dir = get_context('step-2')
checks = []
base = """
from dns_zone_auditor import DnsRecord, validate_zone
soa = DnsRecord('example.com.', 'SOA', 300, ('ns.example.com.', 'hostmaster.example.com.', '1', '7200', '3600', '1209600', '300'))
ns = DnsRecord('example.com.', 'NS', 300, ('ns.example.com.',))
addr = DnsRecord('ns.example.com.', 'A', 300, ('192.0.2.53',))
"""
checks.append(run_case('healthy_zone_has_no_problems', base + r'''
assert validate_zone([soa, ns, addr]) == []
''', workspace))
checks.append(run_case('soa_uniqueness_and_apex', base + r'''
other = DnsRecord('other.example.com.', 'SOA', 300, soa.data)
problems = validate_zone([soa, other, ns, addr])
assert any(p.type == 'SOA_COUNT' and p.severity == 'ERROR' for p in problems)
misplaced = DnsRecord('sub.example.com.', 'SOA', 300, soa.data)
problems2 = validate_zone([misplaced, DnsRecord('sub.example.com.', 'NS', 300, ('ns.example.com.',)), addr])
assert any(p.type == 'SOA_APEX' for p in problems2)
''', workspace))
checks.append(run_case('cname_exclusivity_address_conflict', base + r'''
records = [soa, ns, addr, DnsRecord('alias.example.com.', 'CNAME', 300, ('www.example.com.',)), DnsRecord('alias.example.com.', 'A', 300, ('192.0.2.44',))]
problems = validate_zone(records)
assert any(p.owner == 'alias.example.com.' and p.type == 'CNAME_EXCLUSIVE' for p in problems)
''', workspace))
checks.append(run_case('cname_multiple_detected', base + r'''
records = [soa, ns, addr, DnsRecord('alias.example.com.', 'CNAME', 300, ('one.example.com.',)), DnsRecord('alias.example.com.', 'CNAME', 300, ('two.example.com.',))]
problems = validate_zone(records)
assert any(p.owner == 'alias.example.com.' and p.type == 'CNAME_MULTIPLE' for p in problems)
''', workspace))
checks.append(run_case('apex_ns_missing_detected', base + r'''
problems = validate_zone([soa, addr])
assert any(p.owner == 'example.com.' and p.type == 'APEX_NS_MISSING' for p in problems)
''', workspace))
checks.append(run_case('duplicate_rr_detection', base + r'''
dup = DnsRecord('www.example.com.', 'A', 300, ('192.0.2.10',))
problems = validate_zone([soa, ns, addr, dup, dup])
assert any(p.owner == 'www.example.com.' and p.type == 'DUPLICATE_RR' for p in problems)
''', workspace))
checks.append(run_case('delegation_glue_requirement', base + r'''
child_ns = DnsRecord('child.example.com.', 'NS', 300, ('ns.child.example.com.',))
problems = validate_zone([soa, ns, addr, child_ns])
assert any(p.owner == 'ns.child.example.com.' and p.severity == 'WARNING' and p.type == 'GLUE_MISSING' for p in problems)
''', workspace))
checks.append(run_case('severity_owner_type_sorting', base + r'''
records = [soa, addr, DnsRecord('b.example.com.', 'CNAME', 300, ('x.example.com.',)), DnsRecord('b.example.com.', 'A', 300, ('192.0.2.8',)), DnsRecord('child.example.com.', 'NS', 300, ('ns.child.example.com.',))]
problems = validate_zone(records)
rank = {'ERROR': 0, 'WARNING': 1, 'INFO': 2}
keys = [(p.owner, rank.get(p.severity, 9), p.type, p.message) for p in problems]
assert keys == sorted(keys)
''', workspace))
checks.append(run_case('read_only_records_input', base + r'''
records = [soa, ns, addr]
before = list(records)
problems = validate_zone(records)
assert records == before
assert problems == []
''', workspace))
raise SystemExit(0 if finalize('step-2', checks, reward_dir) else 1)
