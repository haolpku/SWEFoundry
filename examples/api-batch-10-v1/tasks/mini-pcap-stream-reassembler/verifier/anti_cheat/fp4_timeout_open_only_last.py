#!/usr/bin/env python3
from pathlib import Path
import os
import sys

def main():
    workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
    target = workspace / 'environment' / 'codebase' / 'pcap_reassembler' / 'timeouts.py'
    text = target.read_text(encoding='utf-8')
    old = 'return events'
    if old not in text:
        raise SystemExit('expected final return events not found')
    target.write_text(text.replace(old, 'return [] if not events else [events[-1]]', 1), encoding='utf-8')

if __name__ == '__main__':
    main()
