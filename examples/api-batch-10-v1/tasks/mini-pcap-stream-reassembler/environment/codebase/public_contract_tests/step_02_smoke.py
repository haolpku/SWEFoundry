#!/usr/bin/env python3
import pathlib
import struct
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pcap_reassembler import PcapPacket, decode_tcp_segments

def tcp_frame(proto=6):
    eth = b'\x00' * 12 + b'\x08\x00'
    tcp = struct.pack('!HHIIHHHH', 1234, 80, 10, 0, (5 << 12) | 0x18, 4096, 0, 0) + b'hi'
    ip = bytes([0x45, 0, 0, 20 + len(tcp), 0, 0, 0, 0, 64, proto, 0, 0, 10, 0, 0, 1, 10, 0, 0, 2])
    return eth + ip + tcp

def main():
    packets = [PcapPacket(0, 1, 2, len(tcp_frame()), len(tcp_frame()), tcp_frame())]
    segments = decode_tcp_segments(packets)
    assert len(segments) == 1
    assert segments[0].src_ip == '10.0.0.1'
    assert segments[0].dst_port == 80
    assert segments[0].payload == b'hi'
    udp_packets = [PcapPacket(1, 1, 3, len(tcp_frame(17)), len(tcp_frame(17)), tcp_frame(17))]
    assert decode_tcp_segments(udp_packets) == []

if __name__ == '__main__':
    main()
