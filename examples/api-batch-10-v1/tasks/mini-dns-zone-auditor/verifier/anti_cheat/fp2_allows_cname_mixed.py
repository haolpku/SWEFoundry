#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd()))
path = workspace / 'environment' / 'codebase' / 'dns_zone_auditor' / 'validators.py'
text = path.read_text(encoding='utf-8')
old = 'if "CNAME" in types and len(types) > 1:'
new = 'if False and "CNAME" in types and len(types) > 1:'
if old not in text:
    print('required oracle pattern not found: ' + old, file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
