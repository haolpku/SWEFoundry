#!/usr/bin/env python3
import os
from pathlib import Path

workspace = Path(os.environ['TDF_WORKSPACE'])
policy = workspace / 'environment' / 'codebase' / 'mini_systemd_unit_linter' / 'policy.py'
text = policy.read_text(encoding='utf-8')
old = 'WANTS_FAILURE_FATAL = False\n'
new = 'WANTS_FAILURE_FATAL = True\n'
if old not in text:
    raise SystemExit('expected complete Oracle pattern not found: ' + old.strip())
policy.write_text(text.replace(old, new, 1), encoding='utf-8')
