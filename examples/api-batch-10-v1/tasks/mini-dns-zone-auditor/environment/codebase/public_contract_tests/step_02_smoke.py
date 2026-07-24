#!/usr/bin/env python3
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dns_zone_auditor import DnsRecord, validate_zone

records = [
    DnsRecord('example.com.', 'SOA', 300, ('ns.example.com.', 'hostmaster.example.com.', '1', '7200', '3600', '1209600', '300')),
    DnsRecord('bad.example.com.', 'CNAME', 300, ('www.example.com.',)),
    DnsRecord('bad.example.com.', 'A', 300, ('192.0.2.7',)),
]
problems = validate_zone(records)
types = {p.type for p in problems}
assert 'CNAME_EXCLUSIVE' in types
assert 'APEX_NS_MISSING' in types
