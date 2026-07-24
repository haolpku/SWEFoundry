#!/usr/bin/env python3
from pathlib import Path
import os
import sys

def main():
    workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
    target = workspace / 'environment' / 'codebase' / 'pcap_reassembler' / 'streams.py'
    text = target.read_text(encoding='utf-8')
    old = 'start = _sequence_start(segment) - base'
    if old not in text:
        raise SystemExit('expected sequence-normalized start expression not found')
    target.write_text(text.replace(old, 'start = arrival * len(segment.payload)', 1), encoding='utf-8')

if __name__ == '__main__':
    main()
