# Offline MQTT Session Broker State Machine

`mini-mqtt-session-broker` is a five-step, offline Greenfield terminal benchmark candidate in
the `message broker protocol state` domain.

The five cumulative Steps are:

1. `1-parse-broker-events`
2. `2-match-wildcard-subscriptions`
3. `3-replay-qos-and-retained-state`
4. `4-plan-session-migration`
5. `5-integrated-broker-replay-recovery`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
42 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://github.com/eclipse-mosquitto/mosquitto (EPL-2.0); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
