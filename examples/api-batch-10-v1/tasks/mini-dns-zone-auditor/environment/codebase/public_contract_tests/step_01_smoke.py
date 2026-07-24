#!/usr/bin/env python3
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dns_zone_auditor import parse_zone

text = '$TTL 600\nWWW IN A 192.0.2.10\ninfo IN TXT "hello public smoke"\n'
records = parse_zone(text, 'Example.COM')
assert [r.owner for r in records] == ['info.example.com.', 'www.example.com.']
assert [r for r in records if r.type == 'TXT'][0].data == ('hello public smoke',)
assert all(r.ttl == 600 for r in records)
