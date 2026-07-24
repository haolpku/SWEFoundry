#!/usr/bin/env python3
import pathlib
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pcap_reassembler import TcpSegment, compute_tcp_timeouts

def seg(index, src, port, ts, flags=0x18):
    return TcpSegment(index, ts, src, '10.0.0.2', port, 80, 100 + index, 0, flags, b'x')

def main():
    segments = [seg(0, '10.0.0.1', 1111, 1_000_000), seg(1, '10.0.0.3', 2222, 2_000_000), seg(2, '10.0.0.4', 3333, 3_000_000, 0x01)]
    events = compute_tcp_timeouts(segments, 5)
    assert len(events) == 2
    assert events[0].reason == 'idle'
    assert events[0].cutoff_timestamp_us == events[0].last_timestamp_us + 5_000_000
    assert all(e.flow_key[0] != '10.0.0.4' for e in events)

if __name__ == '__main__':
    main()
