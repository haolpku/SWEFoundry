#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from verifier.common import finalize, get_context, run_case

workspace, tests_dir, reward_dir = get_context('step-4')
checks = []
checks.append(run_case('soa_serial_increment_planned', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
soa = DnsRecord('example.com.', 'SOA', 600, ('ns.example.com.', 'hostmaster.example.com.', '2024010101', '7200', '3600', '1209600', '300'))
plan = plan_zone_migration([soa], 300)
assert plan.target_ttl == 300
assert plan.records[0].data[2] == '2024010102'
assert any('SOA serial 2024010101 -> 2024010102' in c for c in plan.changes)
''', workspace))
checks.append(run_case('ttl_normalization_all_records', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
records = [DnsRecord('b.example.com.', 'A', 700, ('192.0.2.2',)), DnsRecord('a.example.com.', 'TXT', 100, ('x',))]
plan = plan_zone_migration(records, 3600)
assert all(r.ttl == 3600 for r in plan.records)
assert set(plan.changes) == {'a.example.com. TXT ttl 100 -> 3600', 'b.example.com. A ttl 700 -> 3600'}
''', workspace))
checks.append(run_case('digest_canonical_order_independent', r'''
import hashlib
from dns_zone_auditor import DnsRecord, plan_zone_migration
records = [DnsRecord('multi.example.com.', 'A', 100, ('192.0.2.2',)), DnsRecord('multi.example.com.', 'A', 100, ('192.0.2.1',))]
plan1 = plan_zone_migration(records, 30)
plan2 = plan_zone_migration(list(reversed(records)), 30)
expected = hashlib.sha256('multi.example.com.|A|30|192.0.2.1\nmulti.example.com.|A|30|192.0.2.2'.encode('utf-8')).hexdigest()
assert plan1.digests['multi.example.com. A'] == expected
assert plan2.digests['multi.example.com. A'] == expected
assert dict(plan1.digests) == dict(plan2.digests)
''', workspace))
checks.append(run_case('already_normalized_without_soa_empty_changes', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
record = DnsRecord('www.example.com.', 'A', 300, ('192.0.2.1',))
plan = plan_zone_migration([record], 300)
assert plan.records == (record,)
assert plan.changes == ()
''', workspace))
checks.append(run_case('digests_are_read_only', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
plan = plan_zone_migration([DnsRecord('www.example.com.', 'A', 300, ('192.0.2.1',))], 300)
try:
    plan.digests['x'] = 'y'
except TypeError:
    pass
else:
    raise AssertionError('digests mapping must be read-only')
''', workspace))
checks.append(run_case('negative_target_ttl_valueerror', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
try:
    plan_zone_migration([DnsRecord('www.example.com.', 'A', 300, ('192.0.2.1',))], -1)
except ValueError:
    pass
else:
    raise AssertionError('negative target_ttl must raise ValueError')
''', workspace))
checks.append(run_case('migration_records_canonical_order', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
records = [DnsRecord('b.example.com.', 'A', 300, ('192.0.2.2',)), DnsRecord('a.example.com.', 'TXT', 300, ('z',)), DnsRecord('a.example.com.', 'A', 300, ('192.0.2.1',))]
plan = plan_zone_migration(records, 300)
keys = [(r.owner, r.type, r.data, r.ttl) for r in plan.records]
assert keys == sorted(keys)
''', workspace))
checks.append(run_case('read_only_records_input', r'''
from dns_zone_auditor import DnsRecord, plan_zone_migration
records = [DnsRecord('www.example.com.', 'A', 500, ('192.0.2.1',))]
before = list(records)
plan_zone_migration(records, 300)
assert records == before
''', workspace))
raise SystemExit(0 if finalize('step-4', checks, reward_dir) else 1)
