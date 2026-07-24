#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd()))
path = workspace / 'environment' / 'codebase' / 'dns_zone_auditor' / 'migration.py'
text = path.read_text(encoding='utf-8')
old = 'return sorted(records, key=lambda r: (r.owner, r.type, r.data, r.ttl))'
new = 'return list(records)'
if old not in text:
    print('required oracle pattern not found: ' + old, file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
