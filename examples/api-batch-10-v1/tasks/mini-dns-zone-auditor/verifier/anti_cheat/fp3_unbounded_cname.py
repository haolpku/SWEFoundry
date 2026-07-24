#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd()))
path = workspace / 'environment' / 'codebase' / 'dns_zone_auditor' / 'resolver.py'
text = path.read_text(encoding='utf-8')
replacements = [
    ('limit = len(by_owner) + 1', 'limit = 1000000000'),
    ("if current in seen:\n            return DnsAnswer(name, typ, \"CNAME_LOOP\", _ordered(answers), tuple(chain))", "if False and current in seen:\n            return DnsAnswer(name, typ, \"CNAME_LOOP\", _ordered(answers), tuple(chain))"),
]
for old, new in replacements:
    if old not in text:
        print('required oracle pattern not found: ' + old, file=sys.stderr)
        sys.exit(2)
    text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
