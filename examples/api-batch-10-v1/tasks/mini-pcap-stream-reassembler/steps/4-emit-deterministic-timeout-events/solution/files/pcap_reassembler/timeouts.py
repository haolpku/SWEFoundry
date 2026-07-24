"""Deterministic timeout event generation from capture timestamps."""
from __future__ import annotations
from dataclasses import dataclass

from .protocols import TcpSegment

@dataclass(frozen=True)
class TcpTimeoutEvent:
    flow_key: tuple[str, int, str, int, str]
    last_timestamp_us: int
    cutoff_timestamp_us: int
    last_packet_index: int
    reason: str

def compute_tcp_timeouts(segments: list[TcpSegment], idle_seconds: int) -> list[TcpTimeoutEvent]:
    if idle_seconds < 0:
        raise ValueError("idle_seconds must be non-negative")
    grouped: dict[tuple[str, int, str, int, str], list[TcpSegment]] = {}
    for segment in segments:
        grouped.setdefault(segment.flow_key, []).append(segment)
    events: list[TcpTimeoutEvent] = []
    idle_us = idle_seconds * 1_000_000
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda s: (s.timestamp_us, s.packet_index, s.sequence))
        if any(s.flags & 0x05 for s in ordered):
            continue
        last = ordered[-1]
        events.append(TcpTimeoutEvent(key, last.timestamp_us, last.timestamp_us + idle_us, last.packet_index, "idle"))
    events.sort(key=lambda e: (e.flow_key, e.cutoff_timestamp_us, e.last_packet_index))
    return events
