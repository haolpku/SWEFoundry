#!/usr/bin/env python3
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dns_zone_auditor import audit_zone

healthy = '$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\n@ IN NS ns\nns IN A 192.0.2.53\nwww IN A 192.0.2.10\nalias IN CNAME www\n'
report = audit_zone(healthy, 'Example.COM', [('alias.example.com', 'A')], 300)
assert report.origin == 'example.com.'
assert report.problems == ()
assert report.answers[0].rcode == 'NOERROR'
assert report.recovery['answer_count'] == '1'

broken = '$TTL 300\n@ IN SOA ns hostmaster 1 7200 3600 1209600 300\nbad IN CNAME www\nbad IN A 192.0.2.9\n'
bad = audit_zone(broken, 'example.com', [('bad.example.com', 'A')], 300)
assert bad.problems
assert len(bad.answers) == 1
