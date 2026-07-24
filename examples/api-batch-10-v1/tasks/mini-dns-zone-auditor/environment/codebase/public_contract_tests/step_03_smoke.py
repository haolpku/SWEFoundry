#!/usr/bin/env python3
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dns_zone_auditor import DnsRecord, answer_zone

records = [
    DnsRecord('www.example.com.', 'A', 300, ('192.0.2.10',)),
    DnsRecord('alias.example.com.', 'CNAME', 300, ('www.example.com.',)),
]
ans = answer_zone(records, 'alias.example.com', 'A')
assert ans.rcode == 'NOERROR'
assert [r.type for r in ans.answers] == ['CNAME', 'A']
assert ans.chain == ('alias.example.com.', 'www.example.com.')
