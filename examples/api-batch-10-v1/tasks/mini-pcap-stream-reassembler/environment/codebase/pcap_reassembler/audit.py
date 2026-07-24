"""Starter integrated audit entry point.

Step 5 replaces this with checkpoint-aware truncation recovery.
"""
from __future__ import annotations
from dataclasses import dataclass

from .pcap import PcapPacket, parse_pcap
from .protocols import TcpSegment, decode_tcp_segments
from .streams import TcpStream, reassemble_tcp_streams
from .timeouts import TcpTimeoutEvent, compute_tcp_timeouts

@dataclass(frozen=True)
class PcapAuditReport:
    packets: tuple[PcapPacket, ...]
    segments: tuple[TcpSegment, ...]
    streams: tuple[TcpStream, ...]
    timeouts: tuple[TcpTimeoutEvent, ...]
    truncated: bool
    truncation_reason: str | None
    errors: tuple[str, ...]
    checkpoint_used: bool

def audit_pcap_streams(data: bytes, checkpoint: bytes | None, idle_seconds: int) -> PcapAuditReport:
    packets = tuple(parse_pcap(data))
    segments = tuple(decode_tcp_segments(list(packets)))
    streams = tuple(reassemble_tcp_streams(list(segments)))
    timeouts = tuple(compute_tcp_timeouts(list(segments), idle_seconds))
    return PcapAuditReport(packets, segments, streams, timeouts, False, None, (), False)
