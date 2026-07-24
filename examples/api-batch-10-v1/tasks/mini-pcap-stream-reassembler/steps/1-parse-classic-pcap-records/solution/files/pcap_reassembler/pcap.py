"""Classic PCAP parser with deterministic endian handling."""
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

def _endian_from_magic(magic: bytes) -> str:
    if magic == b"\xd4\xc3\xb2\xa1":
        return "<"
    if magic == b"\xa1\xb2\xc3\xd4":
        return ">"
    if magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"):
        raise PcapFormatError("nanosecond-resolution pcap is not supported")
    raise PcapFormatError("unsupported pcap magic")

def parse_pcap(data: bytes) -> list[PcapPacket]:
    if len(data) < 24:
        raise PcapFormatError("truncated pcap global header")
    endian = _endian_from_magic(data[:4])
    version_major, version_minor, thiszone, sigfigs, snaplen, network = struct.unpack_from(endian + "HHIIII", data, 4)
    if version_major != 2 or version_minor != 4:
        raise PcapFormatError("unsupported pcap version")
    if snaplen <= 0:
        raise PcapFormatError("invalid pcap snaplen")
    packets: list[PcapPacket] = []
    offset = 24
    index = 0
    while offset < len(data):
        if len(data) - offset < 16:
            raise ValueError("truncated pcap record header")
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack_from(endian + "IIII", data, offset)
        offset += 16
        if ts_usec >= 1_000_000:
            raise PcapFormatError("timestamp microseconds out of range")
        if incl_len > snaplen:
            raise PcapFormatError("captured length exceeds snaplen")
        if incl_len > orig_len:
            raise PcapFormatError("captured length exceeds original length")
        if len(data) - offset < incl_len:
            raise PcapFormatError("truncated pcap packet data")
        packets.append(PcapPacket(index, ts_sec, ts_usec, incl_len, orig_len, bytes(data[offset:offset + incl_len])))
        offset += incl_len
        index += 1
    return packets
