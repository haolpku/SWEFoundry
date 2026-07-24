#!/usr/bin/env python3
import pathlib
import struct
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pcap_reassembler import audit_pcap_streams

def frame(seq, payload, flags=0x18):
    eth = b'\x00' * 12 + b'\x08\x00'
    tcp = struct.pack('!HHIIHHHH', 1234, 80, seq, 0, (5 << 12) | flags, 4096, 0, 0) + payload
    ip = bytes([0x45, 0]) + struct.pack('!H', 20 + len(tcp)) + b'\x00\x00\x00\x00' + bytes([64, 6, 0, 0, 10, 0, 0, 1, 10, 0, 0, 2])
    return eth + ip + tcp

def pcap(records):
    out = [bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)]
    for i, payload in enumerate(records, 1):
        out.append(struct.pack('<IIII', i, 0, len(payload), len(payload)) + payload)
    return b''.join(out)

def main():
    data = pcap([frame(100, b'he'), frame(102, b'llo', 0x19)])
    report = audit_pcap_streams(data, None, 10)
    assert not report.truncated
    assert report.streams[0].data == b'hello'
    assert report.streams[0].closed is True
    truncated = data + struct.pack('<IIII', 9, 0, 20, 20) + b'partial'
    recovered = audit_pcap_streams(truncated, None, 10)
    assert recovered.truncated
    assert recovered.streams[0].data == b'hello'

if __name__ == '__main__':
    main()
