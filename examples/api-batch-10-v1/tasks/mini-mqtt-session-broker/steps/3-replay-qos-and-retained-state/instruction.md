# Step 3: Replay QoS and retained state

Implement `BrokerState` replay through `replay_mqtt_events(events: list[MqttEvent]) -> BrokerState`. The replay must handle QoS 0 and QoS 1 delivery status, acknowledgements, retained message replacement and deletion, durable offline queues, reconnect queue replay, and deterministic ordering.

Disclosed behavioral checks: qos1_awaits_ack, qos1_ack_changes_status, qos1_duplicate_offline_suppression, qos0_immediate_delivery, retained_message_delivered_on_subscribe, retained_delete_tombstone, durable_offline_queue_replayed_on_connect, read_only_broker_state_check.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_03_smoke.py
```
