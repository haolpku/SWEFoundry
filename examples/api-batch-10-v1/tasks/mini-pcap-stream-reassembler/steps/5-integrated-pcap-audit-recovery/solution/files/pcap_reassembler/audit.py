"""Integrated deterministic PCAP stream audit with partial recovery."""
from __future__ import annotations
from dataclasses import dataclass
import json
import struct

from .exceptions import CheckpointError, PcapFormatError
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

def _endian_from_magic(magic: bytes) -> str:
    if magic == b"\xd4\xc3\xb2\xa1":
        return "<"
    if magic == b"\xa1\xb2\xc3\xd4":
        return ">"
    raise PcapFormatError("unsupported pcap magic")

def _parse_pcap_partial(data: bytes) -> tuple[list[PcapPacket], bool, str | None, list[str]]:
    if len(data) < 24:
        return [], True, "global_header", ["truncated pcap global header"]
    try:
        endian = _endian_from_magic(data[:4])
        version_major, version_minor, thiszone, sigfigs, snaplen, network = struct.unpack_from(endian + "HHIIII", data, 4)
    except Exception as exc:
        return [], False, None, [str(exc)]
    if version_major != 2 or version_minor != 4 or snaplen <= 0:
        return [], False, None, ["invalid pcap global header"]
    packets: list[PcapPacket] = []
    errors: list[str] = []
    offset = 24
    index = 0
    while offset < len(data):
        if len(data) - offset < 16:
            return packets, True, "record_header", errors + ["truncated pcap record header"]
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack_from(endian + "IIII", data, offset)
        offset += 16
        if ts_usec >= 1_000_000 or incl_len > snaplen or incl_len > orig_len:
            errors.append("invalid pcap record header")
            break
        if len(data) - offset < incl_len:
            return packets, True, "packet_data", errors + ["truncated pcap packet data"]
        packets.append(PcapPacket(index, ts_sec, ts_usec, incl_len, orig_len, bytes(data[offset:offset + incl_len])))
        offset += incl_len
        index += 1
    return packets, False, None, errors

def _packet_from_json(obj: dict) -> PcapPacket:
    return PcapPacket(int(obj["packet_index"]), int(obj["timestamp_seconds"]), int(obj["timestamp_microseconds"]), int(obj["captured_length"]), int(obj["original_length"]), bytes.fromhex(obj["payload_hex"]))

def _segment_from_json(obj: dict) -> TcpSegment:
    return TcpSegment(int(obj["packet_index"]), int(obj["timestamp_us"]), str(obj["src_ip"]), str(obj["dst_ip"]), int(obj["src_port"]), int(obj["dst_port"]), int(obj["sequence"]), int(obj["acknowledgment"]), int(obj["flags"]), bytes.fromhex(obj["payload_hex"]))

def _load_checkpoint(checkpoint: bytes | None) -> tuple[list[PcapPacket], list[TcpSegment], bool]:
    if checkpoint is None:
        return [], [], False
    try:
        text = checkpoint.decode("utf-8")
        obj = json.loads(text)
    except Exception as exc:
        raise CheckpointError("invalid checkpoint encoding") from exc
    if not isinstance(obj, dict):
        raise CheckpointError("checkpoint must be a json object")
    packets = [_packet_from_json(p) for p in obj.get("packets", [])]
    segments = [_segment_from_json(s) for s in obj.get("segments", [])]
    return packets, segments, True

def _merge_packets(primary: list[PcapPacket], checkpoint_packets: list[PcapPacket]) -> list[PcapPacket]:
    by_index: dict[int, PcapPacket] = {p.packet_index: p for p in checkpoint_packets}
    for packet in primary:
        by_index[packet.packet_index] = packet
    return [by_index[i] for i in sorted(by_index)]

def _merge_segments(primary: list[TcpSegment], checkpoint_segments: list[TcpSegment]) -> list[TcpSegment]:
    by_key: dict[tuple[int, str, int, str, int, int, int], TcpSegment] = {}
    for segment in checkpoint_segments + primary:
        key = (segment.packet_index, segment.src_ip, segment.src_port, segment.dst_ip, segment.dst_port, segment.sequence, len(segment.payload))
        by_key[key] = segment
    return [by_key[k] for k in sorted(by_key)]

def audit_pcap_streams(data: bytes, checkpoint: bytes | None, idle_seconds: int) -> PcapAuditReport:
    checkpoint_packets, checkpoint_segments, checkpoint_used = _load_checkpoint(checkpoint)
    packets, truncated, reason, errors = _parse_pcap_partial(data)
    if not truncated and not errors:
        try:
            packets = parse_pcap(data)
        except Exception as exc:
            errors.append(str(exc))
    decoded = decode_tcp_segments(packets)
    packets = _merge_packets(packets, checkpoint_packets) if checkpoint_used else packets
    segments = _merge_segments(decoded, checkpoint_segments) if checkpoint_used else decoded
    streams = reassemble_tcp_streams(segments)
    timeouts = compute_tcp_timeouts(segments, idle_seconds)
    return PcapAuditReport(tuple(packets), tuple(segments), tuple(streams), tuple(timeouts), bool(truncated), reason, tuple(errors), checkpoint_used)
