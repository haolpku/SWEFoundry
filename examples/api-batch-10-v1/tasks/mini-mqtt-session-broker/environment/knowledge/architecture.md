# Architecture and semantic boundaries

Build Offline MQTT Session Broker State Machine as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-broker-events

Parse JSON broker events for connect, subscribe, publish, acknowledge, disconnect, and expire actions, validate client identifiers and topics, and return events sorted by explicit sequence number.

Verifier semantic categories:
- topic syntax validation
- sequence ordering
- client identifier validation

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-match-wildcard-subscriptions

Implement deterministic MQTT topic filter matching for exact filters, plus wildcards, and terminal hash wildcards, reject malformed filters, and return matching subscription identifiers in lexical order.

Verifier semantic categories:
- wildcard placement rules
- empty topic levels
- stable match ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-replay-qos-and-retained-state

Replay QoS 0 and QoS 1 publish delivery, acknowledgement, retained message replacement, and offline durable session queues from events, returning explicit per-client deliveries in deterministic order.

Verifier semantic categories:
- QoS 1 duplicate suppression
- retained deletion semantics
- durable offline queues

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-plan-session-migration

Generate read-only migration advice for stale subscriptions, unsupported QoS values, retained tombstones, and durable session compaction using only explicit expire events rather than observed elapsed time.

Verifier semantic categories:
- explicit expiry handling
- advice deduplication
- stable session ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-broker-replay-recovery

Integrate event parsing, wildcard matching, QoS replay, retained storage, durable sessions, and migration advice into MqttAuditReport, preserve steps 1 through 4 behavior, and recover deterministically from snapshot plus journal inputs.

Verifier semantic categories:
- steps 1-4 regression
- snapshot compatibility
- journal replay idempotency

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
