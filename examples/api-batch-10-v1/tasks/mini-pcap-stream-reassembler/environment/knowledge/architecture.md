# Architecture and semantic boundaries

Build Classic PCAP TCP Stream Reassembler as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-classic-pcap-records

Parse classic PCAP global headers and packet records from bytes, support declared endian mode and microsecond timestamps as data fields, validate captured lengths, and raise ValueError for truncated record headers.

Verifier semantic categories:
- endianness decoding
- captured length bounds
- record ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-decode-ethernet-ipv4-tcp

Decode Ethernet, IPv4, and TCP headers from parsed packet payloads, validate header lengths and protocol fields, ignore unsupported link frames, and return flow segments ordered by packet index.

Verifier semantic categories:
- IPv4 header length
- TCP data offset
- checksum-neutral parsing

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-reassemble-tcp-streams

Reassemble byte streams per canonical five-tuple flow key, handle out-of-order segments, retransmissions, overlaps, SYN sequence bases, and FIN closure, returning deterministic stream summaries.

Verifier semantic categories:
- overlap resolution
- sequence normalization
- flow key canonicalization

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-emit-deterministic-timeout-events

Generate timeout and incomplete-flow events using explicit packet timestamp fields and a supplied idle threshold, never using live time, and sort events by flow key and cutoff value.

Verifier semantic categories:
- explicit timestamp arithmetic
- FIN and RST handling
- stable event ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-pcap-audit-recovery

Integrate PCAP parsing, protocol decoding, stream reassembly, timeout generation, checkpoint loading, and truncation classification into PcapAuditReport, preserve steps 1 through 4 behavior, and recover deterministic partial results.

Verifier semantic categories:
- steps 1-4 regression
- checkpoint replay
- truncation classification

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
