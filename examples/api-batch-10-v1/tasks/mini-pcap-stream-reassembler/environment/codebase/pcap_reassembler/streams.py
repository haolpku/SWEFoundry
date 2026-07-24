"""Starter TCP stream reassembly.

This starter appends payloads in capture order; Step 3 replaces it.
"""
from __future__ import annotations
from dataclasses import dataclass

from .protocols import TcpSegment

@dataclass(frozen=True)
class TcpStream:
    flow_key: tuple[str, int, str, int, str]
    data: bytes
    closed: bool
    first_packet_index: int
    last_packet_index: int
    base_sequence: int
    gaps: tuple[tuple[int, int], ...]

def reassemble_tcp_streams(segments: list[TcpSegment]) -> list[TcpStream]:
    grouped: dict[tuple[str, int, str, int, str], list[TcpSegment]] = {}
    for segment in segments:
        grouped.setdefault(segment.flow_key, []).append(segment)
    streams: list[TcpStream] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda s: s.packet_index)
        data = b"".join(s.payload for s in ordered)
        base = ordered[0].sequence + (1 if ordered[0].flags & 0x02 else 0)
        streams.append(TcpStream(key, data, any(s.flags & 0x01 for s in ordered), ordered[0].packet_index, ordered[-1].packet_index, base, ()))
    return streams
