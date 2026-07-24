Return only one valid JSON array containing exactly ten objects. No Markdown.

Create the final production portfolio using exactly these ten IDs and themes:

1. `systemd-unit-linter`: systemd unit parsing, dependency graph, activation
   ordering, failure propagation, and deterministic boot-plan replay.
2. `posix-manifest-installer`: filesystem manifest deployment, safe path
   resolution, intent log, rollback, and crash recovery.
3. `dns-zone-auditor`: DNS master-file parsing, RR semantics, CNAME/delegation,
   serial updates, snapshot+journal recovery, fully offline.
4. `wasm-module-auditor`: WebAssembly binary sections, LEB128, type/import/export
   validation, compatibility migration, and integrated binary audit.
5. `png-asset-pipeline`: PNG chunks, CRC/invariants, metadata, deterministic
   transformations, truncated-write recovery, and integrated regression.
6. `mqtt-session-broker`: offline MQTT QoS 0/1 event-state machine, wildcard
   subscriptions, retained messages, durable sessions, replay and migration;
   no sockets or live time.
7. `http-cache-engine`: RFC-inspired cache keys/Vary, freshness with injected
   clock, conditional 304 merge, invalidation/stale policy, disk recovery; no
   network.
8. `ical-sync-engine`: iCalendar parsing, bounded recurrence expansion,
   incremental sync/tombstones, deterministic conflict resolution, snapshot
   migration.
9. `pcap-stream-reassembler`: classic PCAP/Ethernet/IPv4/TCP parsing, flow keys,
   reordering/retransmission, deterministic timeout events, checkpoint and
   truncation recovery.
10. `crdt-notebook-engine`: immutable operations, causal DAG, deterministic
    text merge, peer frontier/tombstone stability, snapshot compaction and
    schema migration.

Use authoritative concept-study sources and plausible licenses:

- systemd repository, LGPL-2.1-or-later;
- POSIX/Open Group specification terms;
- RFC 1034/1035 under IETF Trust Legal Provisions;
- WebAssembly/spec, Apache-2.0;
- W3C PNG specification, W3C Document License;
- Eclipse Mosquitto, EPL-2.0;
- RFC 9111 under IETF Trust Legal Provisions;
- RFC 5545 under IETF Trust Legal Provisions;
- libpcap, BSD-3-Clause;
- Automerge, MIT.

No upstream code may be copied. Python 3.12 standard library only, offline.

Each object must have exactly:

id, title, domain, source_uri, license, provenance, text, capabilities, stages

Use provenance:
{"kind":"open-source-concept-study","copied_code":false,"review_required":true}

Every Topic has exactly five capabilities and five ordered stages. Every stage
has exactly:

id, title, instruction, public_api, public_cases, hidden_categories, mutant

Every instruction has at least 20 words and defines observable behavior. Every
stage has exact Python signatures, at least two public cases, at least three
hidden semantic categories, and one deterministic mutant with exactly `name`
and `deterministic_fault`. Never use hash(), random, wall-clock, UUID, race,
network, locale, or host ordering. Step 5 must add integration/recovery and
regress Steps 1-4. Keep scope implementable in a compact educational codebase.
