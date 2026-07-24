# Public API contract

Package: `pcap_reassembler`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-classic-pcap-records

Public API:
- `class PcapPacket:`
- `def parse_pcap(data: bytes) -> list[PcapPacket]`

Public behavior cases:
- `single-packet-pcap`
- `truncated-record-raises`

## Step 2: 2-decode-ethernet-ipv4-tcp

Public API:
- `class TcpSegment:`
- `def decode_tcp_segments(packets: list[PcapPacket]) -> list[TcpSegment]`

Public behavior cases:
- `ipv4-tcp-segment`
- `udp-frame-ignored`

## Step 3: 3-reassemble-tcp-streams

Public API:
- `class TcpStream:`
- `def reassemble_tcp_streams(segments: list[TcpSegment]) -> list[TcpStream]`

Public behavior cases:
- `out-of-order-reassembled`
- `retransmission-deduplicated`

## Step 4: 4-emit-deterministic-timeout-events

Public API:
- `class TcpTimeoutEvent:`
- `def compute_tcp_timeouts(segments: list[TcpSegment], idle_seconds: int) -> list[TcpTimeoutEvent]`

Public behavior cases:
- `idle-flow-timeout`
- `closed-flow-no-timeout`

## Step 5: 5-integrated-pcap-audit-recovery

Public API:
- `class PcapAuditReport:`
- `def audit_pcap_streams(data: bytes, checkpoint: bytes | None, idle_seconds: int) -> PcapAuditReport`

Public behavior cases:
- `complete-stream-audit`
- `truncated-capture-recovery`
