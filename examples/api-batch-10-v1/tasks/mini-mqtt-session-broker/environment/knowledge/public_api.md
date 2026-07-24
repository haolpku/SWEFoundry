# Public API contract

Package: `mqtt_session_broker`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-broker-events

Public API:
- `class MqttEvent:`
- `def parse_mqtt_events(text: str) -> list[MqttEvent]`

Public behavior cases:
- `connect-subscribe-publish-events`
- `duplicate-sequence-raises`

## Step 2: 2-match-wildcard-subscriptions

Public API:
- `class Subscription:`
- `def match_mqtt_subscriptions(subscriptions: list[Subscription], topic: str) -> list[str]`

Public behavior cases:
- `single-level-wildcard-match`
- `multi-level-wildcard-match`

## Step 3: 3-replay-qos-and-retained-state

Public API:
- `class BrokerState:`
- `def replay_mqtt_events(events: list[MqttEvent]) -> BrokerState`

Public behavior cases:
- `qos1-awaits-ack`
- `retained-message-delivered-on-subscribe`

## Step 4: 4-plan-session-migration

Public API:
- `class MqttMigrationAdvice:`
- `def plan_mqtt_migration(state: BrokerState) -> list[MqttMigrationAdvice]`

Public behavior cases:
- `unsupported-qos-advice`
- `compaction-advice-for-acked-deliveries`

## Step 5: 5-integrated-broker-replay-recovery

Public API:
- `class MqttAuditReport:`
- `def audit_mqtt_session(snapshot: str | None, journal: str) -> MqttAuditReport`

Public behavior cases:
- `fresh-journal-audit`
- `snapshot-journal-recovery-audit`
