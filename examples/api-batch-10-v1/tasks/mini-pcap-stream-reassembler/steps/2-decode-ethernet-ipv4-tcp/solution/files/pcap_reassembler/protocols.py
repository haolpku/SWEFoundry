"""Deterministic Ethernet, IPv4, and TCP decoder."""
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
    segments: list[TcpSegment] = []
    for packet in sorted(packets, key=lambda p: p.packet_index):
        frame = packet.payload
        if len(frame) < 14:
            continue
        ether_type = int.from_bytes(frame[12:14], "big")
        if ether_type != 0x0800:
            continue
        ip = frame[14:]
        if len(ip) < 20:
            continue
        version = ip[0] >> 4
        ihl = (ip[0] & 0x0F) * 4
        if version != 4 or ihl < 20 or len(ip) < ihl:
            continue
        total_length = int.from_bytes(ip[2:4], "big")
        if total_length < ihl or total_length > len(ip):
            continue
        flags_fragment = int.from_bytes(ip[6:8], "big")
        fragment_offset = flags_fragment & 0x1FFF
        more_fragments = bool(flags_fragment & 0x2000)
        if fragment_offset != 0 or more_fragments:
            continue
        if ip[9] != 6:
            continue
        tcp = ip[ihl:total_length]
        if len(tcp) < 20:
            continue
        src_port, dst_port, seq, ack, offset_flags = struct.unpack_from("!HHIIH", tcp, 0)
        data_offset = (offset_flags >> 12) * 4
        if data_offset < 20 or len(tcp) < data_offset:
            continue
        flags = offset_flags & 0x01FF
        payload = bytes(tcp[data_offset:])
        segments.append(TcpSegment(packet.packet_index, packet.timestamp_us, _ip(ip[12:16]), _ip(ip[16:20]), src_port, dst_port, seq, ack, flags, payload))
    return segments
