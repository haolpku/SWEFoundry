#!/usr/bin/env python3
from pathlib import Path
import os
import sys

def main():
    workspace = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TDF_WORKSPACE', '.')).resolve()
    target = workspace / 'environment' / 'codebase' / 'pcap_reassembler' / 'pcap.py'
    text = target.read_text(encoding='utf-8')
    old = "if magic == b'\\xa1\\xb2\\xc3\\xd4':\n        return '>'"
    if old not in text:
        old = 'if magic == b"\\xa1\\xb2\\xc3\\xd4":\n        return ">"'
    if old not in text:
        raise SystemExit('expected big-endian magic branch not found')
    new = old.split(chr(10))[0] + chr(10) + "        return '<'"
    target.write_text(text.replace(old, new, 1), encoding='utf-8')

if __name__ == '__main__':
    main()
