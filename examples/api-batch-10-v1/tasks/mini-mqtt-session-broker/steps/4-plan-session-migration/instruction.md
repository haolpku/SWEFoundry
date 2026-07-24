# Step 4: Plan session migration

Implement `MqttMigrationAdvice` and `plan_mqtt_migration(state: BrokerState) -> list[MqttMigrationAdvice]`. The planner must be read-only and deterministic. It reports unsupported QoS values, explicit expire stale sessions, retained tombstones, and compaction opportunities for acknowledged QoS 1 deliveries. It must not infer expiry from live time or elapsed wall-clock observations.

Disclosed behavioral checks: unsupported_qos_advice, explicit_expire_stale_session, no_live_time_expiry_without_expire, retained_tombstone_advice, compaction_advice_for_acked_qos1, advice_deduplicated, stable_advice_ordering, read_only_planning_state_check.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_04_smoke.py
```
