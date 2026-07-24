from __future__ import annotations

CHECKS: dict[str, list[tuple[str, str]]] = {
    'step-1': [
        ('little_endian_single_packet_public', r'''
data = make_pcap([(3, 4, b'abc')], endian='<')
packets = parse_pcap(data)
assert len(packets) == 1
assert packets[0].packet_index == 0
assert packets[0].timestamp_us == 3000004
assert packets[0].payload == b'abc'
'''),
        ('big_endian_declared_magic_hidden_endianness_decoding', r'''
data = make_pcap([(9, 123456, b'be')], endian='>')
packets = parse_pcap(data)
assert len(packets) == 1
assert packets[0].timestamp_seconds == 9
assert packets[0].timestamp_microseconds == 123456
assert packets[0].captured_length == 2
'''),
        ('truncated_record_header_raises_valueerror_public', r'''
header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
try:
    parse_pcap(header + b'abc')
except ValueError:
    pass
else:
    raise AssertionError('expected ValueError for truncated record header')
'''),
        ('captured_length_exceeds_snaplen_hidden_bounds', r'''
header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 3, 1)
record = struct.pack('<IIII', 1, 0, 4, 4) + b'abcd'
try:
    parse_pcap(header + record)
except ValueError:
    pass
else:
    raise AssertionError('incl_len greater than snaplen must fail')
'''),
        ('captured_length_exceeds_original_hidden_bounds', r'''
header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
record = struct.pack('<IIII', 1, 0, 4, 3) + b'abcd'
try:
    parse_pcap(header + record)
except ValueError:
    pass
else:
    raise AssertionError('incl_len greater than orig_len must fail')
'''),
        ('timestamp_microseconds_range_hidden_data_field', r'''
header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
record = struct.pack('<IIII', 1, 1000000, 1, 1) + b'x'
try:
    parse_pcap(header + record)
except ValueError:
    pass
else:
    raise AssertionError('ts_usec outside microsecond range must fail')
'''),
        ('record_ordering_indices_hidden_record_ordering', r'''
data = make_pcap([(1, 0, b'a'), (1, 1, b'b'), (1, 2, b'c')], endian='<')
packets = parse_pcap(data)
assert [p.packet_index for p in packets] == [0, 1, 2]
assert [p.payload for p in packets] == [b'a', b'b', b'c']
'''),
        ('read_only_state_repeated_parse_no_mutation', r'''
data = make_pcap([(2, 2, b'immutable')], endian='<')
before = bytes(data)
first = parse_pcap(data)
second = parse_pcap(data)
assert data == before
assert first == second
assert first[0].payload == b'immutable'
'''),
    ],
    'step-2': [
        ('ipv4_tcp_segment_public', r'''
frame = eth_ipv4_tcp(seq=10, payload=b'hi')
packets = [PcapPacket(0, 1, 5, len(frame), len(frame), frame)]
segments = decode_tcp_segments(packets)
assert len(segments) == 1
assert segments[0].src_ip == '10.0.0.1'
assert segments[0].dst_ip == '10.0.0.2'
assert segments[0].payload == b'hi'
'''),
        ('udp_frame_ignored_public', r'''
frame = eth_ipv4_udp()
packets = [PcapPacket(0, 1, 0, len(frame), len(frame), frame)]
assert decode_tcp_segments(packets) == []
'''),
        ('non_ipv4_ethernet_ignored', r'''
frame = b'\x00' * 12 + struct.pack('!H', 0x86dd) + b'not-ipv4'
packets = [PcapPacket(0, 1, 0, len(frame), len(frame), frame)]
assert decode_tcp_segments(packets) == []
'''),
        ('ipv4_options_header_length_hidden', r'''
frame = eth_ipv4_tcp(seq=20, payload=b'option-ip', ip_options=b'\x01\x01\x01\x01')
packets = [PcapPacket(0, 1, 0, len(frame), len(frame), frame)]
segments = decode_tcp_segments(packets)
assert len(segments) == 1
assert segments[0].sequence == 20
assert segments[0].payload == b'option-ip'
'''),
        ('tcp_options_data_offset_hidden', r'''
frame = eth_ipv4_tcp(seq=30, payload=b'option-tcp', tcp_options=b'\x01\x01\x01\x01')
packets = [PcapPacket(0, 1, 0, len(frame), len(frame), frame)]
segments = decode_tcp_segments(packets)
assert len(segments) == 1
assert segments[0].payload == b'option-tcp'
'''),
        ('fragmented_ipv4_ignored_protocol_validation', r'''
frame = eth_ipv4_tcp(seq=40, payload=b'frag', fragment=0x2000)
packets = [PcapPacket(0, 1, 0, len(frame), len(frame), frame)]
assert decode_tcp_segments(packets) == []
'''),
        ('packet_index_ordering_hidden', r'''
a = eth_ipv4_tcp(seq=1, payload=b'a')
b = eth_ipv4_tcp(seq=2, payload=b'b')
packets = [PcapPacket(9, 1, 0, len(a), len(a), a), PcapPacket(3, 1, 0, len(b), len(b), b)]
segments = decode_tcp_segments(packets)
assert [s.packet_index for s in segments] == [3, 9]
assert [s.payload for s in segments] == [b'b', b'a']
'''),
        ('read_only_state_packets_no_mutation', r'''
frame = eth_ipv4_tcp(seq=50, payload=b'ro')
packet = PcapPacket(0, 1, 0, len(frame), len(frame), frame)
before = packet.payload
first = decode_tcp_segments([packet])
second = decode_tcp_segments([packet])
assert packet.payload == before
assert first == second
'''),
    ],
    'step-3': [
        ('out_of_order_reassembled_public_sequence_order', r'''
segments = [TcpSegment(1, 2000, '10.0.0.1', '10.0.0.2', 1111, 80, 104, 0, 0x18, b'o'), TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 100, 0, 0x18, b'hell')]
streams = reassemble_tcp_streams(segments)
assert len(streams) == 1
assert streams[0].data == b'hello'
'''),
        ('retransmission_deduplicated_public', r'''
segments = [TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 100, 0, 0x18, b'abc'), TcpSegment(1, 1001, '10.0.0.1', '10.0.0.2', 1111, 80, 100, 0, 0x18, b'abc')]
streams = reassemble_tcp_streams(segments)
assert streams[0].data == b'abc'
'''),
        ('overlap_resolution_first_byte_wins_hidden', r'''
segments = [TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 100, 0, 0x18, b'abc'), TcpSegment(1, 1001, '10.0.0.1', '10.0.0.2', 1111, 80, 102, 0, 0x18, b'CDE')]
streams = reassemble_tcp_streams(segments)
assert streams[0].data == b'abcDE'
'''),
        ('syn_sequence_base_normalization_hidden', r'''
segments = [TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 5000, 0, 0x02, b''), TcpSegment(1, 1001, '10.0.0.1', '10.0.0.2', 1111, 80, 5001, 0, 0x18, b'data')]
streams = reassemble_tcp_streams(segments)
assert streams[0].base_sequence == 5001
assert streams[0].data == b'data'
'''),
        ('canonical_flow_key_sorting_hidden', r'''
segments = [TcpSegment(1, 1001, '10.0.0.9', '10.0.0.2', 2222, 80, 1, 0, 0x18, b'b'), TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'a')]
streams = reassemble_tcp_streams(segments)
assert [s.flow_key for s in streams] == sorted(s.flow_key for s in streams)
'''),
        ('fin_sets_closed_state_hidden', r'''
segments = [TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'x'), TcpSegment(1, 1001, '10.0.0.1', '10.0.0.2', 1111, 80, 2, 0, 0x01, b'')]
streams = reassemble_tcp_streams(segments)
assert streams[0].closed is True
'''),
        ('gap_summary_hidden_overlap_resolution', r'''
segments = [TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 100, 0, 0x18, b'ab'), TcpSegment(1, 1001, '10.0.0.1', '10.0.0.2', 1111, 80, 104, 0, 0x18, b'ef')]
streams = reassemble_tcp_streams(segments)
assert streams[0].data == b'abef'
assert streams[0].gaps == ((2, 4),)
'''),
        ('read_only_state_segments_no_mutation', r'''
segments = [TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'ro')]
before = list(segments)
first = reassemble_tcp_streams(segments)
second = reassemble_tcp_streams(segments)
assert segments == before
assert first == second
'''),
    ],
    'step-4': [
        ('idle_flow_timeout_public', r'''
segments = [TcpSegment(0, 1000000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'a')]
events = compute_tcp_timeouts(segments, 7)
assert len(events) == 1
assert events[0].last_timestamp_us == 1000000
assert events[0].cutoff_timestamp_us == 8000000
assert events[0].reason == 'idle'
'''),
        ('closed_flow_no_timeout_public_fin', r'''
segments = [TcpSegment(0, 1000000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x01, b'')]
assert compute_tcp_timeouts(segments, 7) == []
'''),
        ('rst_closed_flow_no_timeout_hidden', r'''
segments = [TcpSegment(0, 1000000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x04, b'')]
assert compute_tcp_timeouts(segments, 7) == []
'''),
        ('all_open_flows_reported_hidden_not_last_only', r'''
segments = [TcpSegment(0, 1000000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'a'), TcpSegment(1, 2000000, '10.0.0.3', '10.0.0.4', 2222, 80, 1, 0, 0x18, b'b')]
events = compute_tcp_timeouts(segments, 3)
assert len(events) == 2
assert {e.flow_key[0] for e in events} == {'10.0.0.1', '10.0.0.3'}
'''),
        ('explicit_timestamp_arithmetic_hidden_no_live_time', r'''
segments = [TcpSegment(5, 1234567, '10.0.0.5', '10.0.0.6', 3333, 80, 1, 0, 0x18, b'a')]
event = compute_tcp_timeouts(segments, 0)[0]
assert event.cutoff_timestamp_us == 1234567
assert event.last_packet_index == 5
'''),
        ('stable_event_ordering_hidden', r'''
segments = [TcpSegment(2, 5000000, '10.0.0.9', '10.0.0.1', 9, 80, 1, 0, 0x18, b'a'), TcpSegment(1, 4000000, '10.0.0.1', '10.0.0.1', 1, 80, 1, 0, 0x18, b'a')]
events = compute_tcp_timeouts(segments, 1)
assert [(e.flow_key, e.cutoff_timestamp_us) for e in events] == sorted((e.flow_key, e.cutoff_timestamp_us) for e in events)
'''),
        ('negative_idle_seconds_raises', r'''
try:
    compute_tcp_timeouts([], -1)
except ValueError:
    pass
else:
    raise AssertionError('negative idle_seconds must raise')
'''),
        ('read_only_state_segments_no_mutation', r'''
segments = [TcpSegment(0, 1000000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'ro')]
before = list(segments)
first = compute_tcp_timeouts(segments, 1)
second = compute_tcp_timeouts(segments, 1)
assert segments == before
assert first == second
'''),
    ],
    'step-5': [
        ('complete_stream_audit_public_integrated', r'''
frames = [eth_ipv4_tcp(seq=100, flags=0x02, payload=b''), eth_ipv4_tcp(seq=101, flags=0x18, payload=b'he'), eth_ipv4_tcp(seq=103, flags=0x19, payload=b'llo')]
data = make_pcap([(1, 0, frames[0]), (2, 0, frames[1]), (3, 0, frames[2])])
report = audit_pcap_streams(data, None, 5)
assert report.truncated is False
assert report.truncation_reason is None
assert len(report.packets) == 3
assert report.streams[0].data == b'hello'
assert report.streams[0].closed is True
assert report.timeouts == ()
'''),
        ('truncated_capture_recovery_public_preserves_partial_stream', r'''
first = eth_ipv4_tcp(seq=100, flags=0x18, payload=b'keep')
second = eth_ipv4_tcp(seq=104, flags=0x18, payload=b'later')
full = make_pcap([(1, 0, first), (2, 0, second)])
truncated = full[:-3]
report = audit_pcap_streams(truncated, None, 9)
assert report.truncated is True
assert report.truncation_reason == 'packet_data'
assert report.streams[0].data == b'keep'
assert any('truncated pcap packet data' in e for e in report.errors)
'''),
        ('checkpoint_replay_migration_hidden', r'''
segment = {'packet_index': 7, 'timestamp_us': 7000000, 'src_ip': '10.1.1.1', 'dst_ip': '10.1.1.2', 'src_port': 7777, 'dst_port': 80, 'sequence': 100, 'acknowledgment': 0, 'flags': 24, 'payload_hex': '63686b'}
checkpoint = checkpoint_json(segments=[segment])
empty_capture = make_pcap([])
report = audit_pcap_streams(empty_capture, checkpoint, 2)
assert report.checkpoint_used is True
assert report.streams[0].data == b'chk'
assert report.timeouts[0].flow_key == ('10.1.1.1', 7777, '10.1.1.2', 80, 'tcp')
'''),
        ('step1_big_endian_regression_hidden', r'''
data = make_pcap([(4, 5, b'be')], endian='>')
packets = parse_pcap(data)
assert packets[0].timestamp_us == 4000005
'''),
        ('step2_ipv4_options_regression_hidden', r'''
frame = eth_ipv4_tcp(seq=20, payload=b'ipopt', ip_options=b'\x01\x01\x01\x01')
packet = PcapPacket(0, 1, 0, len(frame), len(frame), frame)
segments = decode_tcp_segments([packet])
assert len(segments) == 1
assert segments[0].payload == b'ipopt'
'''),
        ('step3_out_of_order_regression_hidden', r'''
segments = [TcpSegment(1, 2000, '10.0.0.1', '10.0.0.2', 1111, 80, 104, 0, 0x18, b'o'), TcpSegment(0, 1000, '10.0.0.1', '10.0.0.2', 1111, 80, 100, 0, 0x18, b'hell')]
assert reassemble_tcp_streams(segments)[0].data == b'hello'
'''),
        ('step4_all_open_flows_timeout_regression_hidden', r'''
segments = [TcpSegment(0, 1000000, '10.0.0.1', '10.0.0.2', 1111, 80, 1, 0, 0x18, b'a'), TcpSegment(1, 2000000, '10.0.0.3', '10.0.0.4', 2222, 80, 1, 0, 0x18, b'b')]
assert len(compute_tcp_timeouts(segments, 3)) == 2
'''),
        ('invalid_checkpoint_raises_checkpoint_error_hidden', r'''
try:
    audit_pcap_streams(make_pcap([]), b'not-json', 1)
except ValueError:
    pass
else:
    raise AssertionError('invalid checkpoint must raise ValueError-compatible exception')
'''),
        ('read_only_state_integrated_audit_no_mutation', r'''
frame = eth_ipv4_tcp(seq=100, flags=0x18, payload=b'ro')
data = make_pcap([(1, 0, frame)])
before = bytes(data)
first = audit_pcap_streams(data, None, 1)
second = audit_pcap_streams(data, None, 1)
assert data == before
assert first == second
'''),
    ],
}


def get_checks(step_id: str) -> list[tuple[str, str]]:
    return CHECKS[step_id]
