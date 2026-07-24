# Step 5: Integrated broker replay recovery

Implement `MqttAuditReport` integration and `audit_mqtt_session(snapshot: str | None, journal: str) -> MqttAuditReport`. The integrated audit must parse snapshot and journal event lists, recover deterministically, replay retained state and durable sessions, generate migration advice, and preserve all critical Step 1 through Step 4 behaviors.

Disclosed behavioral checks: fresh_journal_audit_counts, snapshot_journal_recovery_retains_messages, journal_replay_idempotent_ordering, parse_regression_sequence_sort_and_validation, match_regression_wildcard_integrated, replay_regression_qos_ack, migration_regression_advice, critical_duplicate_sequence_rejected_across_snapshot_journal, read_only_audit_report_state_check.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_05_smoke.py
```
