# Step 1: Parse broker events

Implement `class MqttEvent` support and `parse_mqtt_events(text: str) -> list[MqttEvent]` for JSON connect, subscribe, publish, acknowledge, disconnect, and expire events. Validate client identifiers, topic names, topic filters, QoS shape, duplicate sequence numbers, and return events sorted by explicit `seq`.

Disclosed behavioral checks: sorted_by_explicit_sequence, duplicate_sequence_rejected, invalid_client_identifier_rejected, publish_topic_wildcard_rejected, malformed_subscribe_filter_rejected, empty_topic_level_rejected, action_and_alias_fields_preserved, read_only_event_state_check.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_01_smoke.py
```
