"""Deterministic TCP byte-stream reassembly."""
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

def _sequence_start(segment: TcpSegment) -> int:
    return segment.sequence + (1 if segment.flags & 0x02 else 0)

def reassemble_tcp_streams(segments: list[TcpSegment]) -> list[TcpStream]:
    grouped: dict[tuple[str, int, str, int, str], list[TcpSegment]] = {}
    for segment in segments:
        grouped.setdefault(segment.flow_key, []).append(segment)
    streams: list[TcpStream] = []
    for key in sorted(grouped):
        members = sorted(grouped[key], key=lambda s: (s.packet_index, s.sequence))
        data_segments = [s for s in members if s.payload]
        base_candidates = [_sequence_start(s) for s in members if s.flags & 0x02]
        if base_candidates:
            base = min(base_candidates)
        elif data_segments:
            base = min(_sequence_start(s) for s in data_segments)
        else:
            base = _sequence_start(members[0])
        pieces: list[tuple[int, int, bytes]] = []
        for arrival, segment in enumerate(members):
            start = _sequence_start(segment) - base
            if segment.payload:
                pieces.append((start, arrival, segment.payload))
        occupied: dict[int, tuple[int, int]] = {}
        for start, arrival, payload in sorted(pieces, key=lambda p: (p[0], p[1])):
            for i, byte in enumerate(payload):
                pos = start + i
                if pos < 0:
                    continue
                if pos not in occupied:
                    occupied[pos] = (arrival, byte)
        if occupied:
            max_pos = max(occupied)
            data_bytes = bytearray()
            gaps: list[tuple[int, int]] = []
            pos = 0
            while pos <= max_pos:
                if pos in occupied:
                    data_bytes.append(occupied[pos][1])
                    pos += 1
                    continue
                gap_start = pos
                while pos <= max_pos and pos not in occupied:
                    pos += 1
                gaps.append((gap_start, pos))
            data = bytes(data_bytes)
        else:
            data = b""
            gaps = []
        streams.append(TcpStream(key, data, any(s.flags & 0x05 for s in members), min(s.packet_index for s in members), max(s.packet_index for s in members), base, tuple(gaps)))
    return streams
