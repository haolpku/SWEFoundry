"""Starter Ethernet/IPv4/TCP decoding.

This version assumes twenty-byte IPv4 headers; Step 2 replaces it.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

from .pcap import PcapPacket

@dataclass(frozen=True)
class TcpSegment:
    packet_index: int
    timestamp_us: int
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    sequence: int
    acknowledgment: int
    flags: int
    payload: bytes

    @property
    def flow_key(self) -> tuple[str, int, str, int, str]:
        return (self.src_ip, self.src_port, self.dst_ip, self.dst_port, "tcp")

def _ip(raw: bytes) -> str:
    return ".".join(str(b) for b in raw)

def decode_tcp_segments(packets: list[PcapPacket]) -> list[TcpSegment]:
    out: list[TcpSegment] = []
    for packet in sorted(packets, key=lambda p: p.packet_index):
        frame = packet.payload
        if len(frame) < 14 or int.from_bytes(frame[12:14], "big") != 0x0800:
            continue
        ip = frame[14:]
        if len(ip) < 20 or (ip[0] >> 4) != 4 or ip[9] != 6:
            continue
        total_len = int.from_bytes(ip[2:4], "big")
        tcp_start = 20
        tcp = ip[tcp_start:total_len]
        if len(tcp) < 20:
            continue
        src_port, dst_port, seq, ack, offset_flags = struct.unpack_from("!HHIIH", tcp, 0)
        tcp_len = (offset_flags >> 12) * 4
        if tcp_len < 20 or len(tcp) < tcp_len:
            continue
        out.append(TcpSegment(packet.packet_index, packet.timestamp_us, _ip(ip[12:16]), _ip(ip[16:20]), src_port, dst_port, seq, ack, offset_flags & 0x01FF, tcp[tcp_len:]))
    return out
