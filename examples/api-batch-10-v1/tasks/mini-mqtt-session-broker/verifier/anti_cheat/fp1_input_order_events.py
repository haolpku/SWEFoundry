#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target = workspace / 'environment' / 'codebase' / 'mqtt_session_broker' / 'parser.py'
    text = target.read_text(encoding='utf-8')
    old = '    return sorted(events, key=lambda event: event.seq)\n'
    new = '    return events\n'
    if old not in text:
        raise SystemExit('oracle parser sort pattern not found')
    target.write_text(text.replace(old, new, 1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
