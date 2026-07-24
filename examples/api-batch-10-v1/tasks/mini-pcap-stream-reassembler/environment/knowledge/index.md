# Knowledge index

This local corpus defines the public surface and engineering boundaries for
`mini-pcap-stream-reassembler`. It is agent-visible at `/app/knowledge` and is the authoritative
contract for the offline benchmark.

Documents:

- `public_api.md`: exact public signatures and named public behavior cases.
- `public_api.json`: machine-readable Step 1–5 contract.
- `architecture.md`: subsystem progression, semantic boundaries, and integration rules.

Provenance:

The task is a concept study informed by https://github.com/the-tcpdump-group/libpcap, licensed as
BSD-3-Clause. No upstream implementation code or proprietary data was
copied. The citation supplies domain framing only; the benchmark implementation
and tests are newly authored and remain under expert review.
