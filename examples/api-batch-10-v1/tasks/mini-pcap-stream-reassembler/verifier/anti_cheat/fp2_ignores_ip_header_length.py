#!/usr/bin/env python3
from pathlib import Path
import os
import sys

def main():
    workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
    target = workspace / 'environment' / 'codebase' / 'pcap_reassembler' / 'protocols.py'
    text = target.read_text(encoding='utf-8')
    old = 'tcp = ip[ihl:total_length]'
    if old not in text:
        raise SystemExit('expected TCP slice using ihl not found')
    target.write_text(text.replace(old, 'tcp = ip[20:total_length]', 1), encoding='utf-8')

if __name__ == '__main__':
    main()
