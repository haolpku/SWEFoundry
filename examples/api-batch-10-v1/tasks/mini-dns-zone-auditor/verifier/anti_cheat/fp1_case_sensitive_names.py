#!/usr/bin/env python3
import os
import sys
from pathlib import Path

workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd()))
path = workspace / 'environment' / 'codebase' / 'dns_zone_auditor' / 'parser.py'
text = path.read_text(encoding='utf-8')
replacements = [
    ("return (origin if origin.endswith(\".\") else origin + \".\").lower()", "return origin if origin.endswith(\".\") else origin + \".\""),
    ("return name.lower()", "return name"),
    ("return (name + \".\" + origin).lower()", "return name + \".\" + origin"),
]
for old, new in replacements:
    if old not in text:
        print('required oracle pattern not found: ' + old, file=sys.stderr)
        sys.exit(2)
    text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
