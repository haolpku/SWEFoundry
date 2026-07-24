#!/usr/bin/env python3
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dns_zone_auditor import DnsRecord, plan_zone_migration

soa = DnsRecord('example.com.', 'SOA', 600, ('ns.example.com.', 'hostmaster.example.com.', '2024010101', '7200', '3600', '1209600', '300'))
plan = plan_zone_migration([soa], 300)
assert plan.records[0].ttl == 300
assert plan.records[0].data[2] == '2024010102'
assert 'example.com. SOA' in next(iter(plan.digests))
unchanged = plan_zone_migration([DnsRecord('www.example.com.', 'A', 300, ('192.0.2.1',))], 300)
assert unchanged.changes == ()
