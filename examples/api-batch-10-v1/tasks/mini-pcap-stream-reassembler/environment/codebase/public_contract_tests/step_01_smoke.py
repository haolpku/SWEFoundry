#!/usr/bin/env python3
import pathlib
import struct
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pcap_reassembler import parse_pcap

def main():
    header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
    payload = b'abc'
    data = header + struct.pack('<IIII', 7, 8, len(payload), len(payload)) + payload
    packets = parse_pcap(data)
    assert len(packets) == 1
    assert packets[0].timestamp_seconds == 7
    assert packets[0].timestamp_microseconds == 8
    assert packets[0].payload == payload
    try:
        parse_pcap(header + b'abc')
    except ValueError:
        pass
    else:
        raise AssertionError('truncated record header must raise ValueError')

if __name__ == '__main__':
    main()
