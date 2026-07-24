# Step 2: Match wildcard subscriptions

Implement deterministic `Subscription` handling and `match_mqtt_subscriptions(subscriptions: list[Subscription], topic: str) -> list[str]`. Exact filters, `+` single-level wildcards, and terminal `#` multi-level wildcards are supported. Malformed filters and topics are rejected, and matching subscription identifiers are returned in lexical order.

Disclosed behavioral checks: exact_filter_match, single_level_wildcard_match, terminal_hash_wildcard_match, hash_not_partial_topic_level, hash_must_be_terminal, plus_whole_level_only, lexical_identifier_order, invalid_topic_wildcard_rejected, read_only_subscription_state_check.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_02_smoke.py
```
