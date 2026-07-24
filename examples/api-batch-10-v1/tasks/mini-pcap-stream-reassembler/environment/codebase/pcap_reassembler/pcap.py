"""Starter classic PCAP parsing helpers.

This starter intentionally supports only little-endian captures. Step 1 replaces
it with a complete endian-aware parser.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

from .exceptions import PcapFormatError

@dataclass(frozen=True)
class PcapPacket:
    packet_index: int
    timestamp_seconds: int
    timestamp_microseconds: int
    captured_length: int
    original_length: int
    payload: bytes

    @property
    def timestamp_us(self) -> int:
        return self.timestamp_seconds * 1_000_000 + self.timestamp_microseconds

def parse_pcap(data: bytes) -> list[PcapPacket]:
    if len(data) < 24:
        raise PcapFormatError("truncated pcap global header")
    magic = data[:4]
    if magic != b"\xd4\xc3\xb2\xa1":
        raise PcapFormatError("starter parser only accepts little-endian microsecond pcap")
    version_major, version_minor, thiszone, sigfigs, snaplen, network = struct.unpack_from("<HHIIII", data, 4)
    if version_major != 2 or version_minor != 4:
        raise PcapFormatError("unsupported pcap version")
    packets: list[PcapPacket] = []
    offset = 24
    index = 0
    while offset < len(data):
        if len(data) - offset < 16:
            raise ValueError("truncated pcap record header")
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack_from("<IIII", data, offset)
        offset += 16
        if incl_len > snaplen or incl_len > orig_len:
            raise PcapFormatError("invalid captured length")
        if len(data) - offset < incl_len:
            raise PcapFormatError("truncated pcap packet data")
        packets.append(PcapPacket(index, ts_sec, ts_usec, incl_len, orig_len, data[offset:offset + incl_len]))
        offset += incl_len
        index += 1
    return packets
