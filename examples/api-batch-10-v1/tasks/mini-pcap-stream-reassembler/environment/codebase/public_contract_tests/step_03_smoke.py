#!/usr/bin/env python3
import pathlib
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pcap_reassembler import TcpSegment, reassemble_tcp_streams

def seg(index, seq, payload, flags=0x18):
    return TcpSegment(index, 1000 + index, '10.0.0.1', '10.0.0.2', 1111, 80, seq, 0, flags, payload)

def main():
    segments = [seg(2, 104, b'o'), seg(0, 100, b'hell'), seg(1, 100, b'hell')]
    streams = reassemble_tcp_streams(segments)
    assert len(streams) == 1
    assert streams[0].data == b'hello'
    assert streams[0].flow_key == ('10.0.0.1', 1111, '10.0.0.2', 80, 'tcp')

if __name__ == '__main__':
    main()
