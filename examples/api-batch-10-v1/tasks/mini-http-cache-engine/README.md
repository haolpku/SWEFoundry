# Offline HTTP Cache Semantics Engine

`mini-http-cache-engine` is a five-step, offline Greenfield terminal benchmark candidate in
the `HTTP caching and persistence` domain.

The five cumulative Steps are:

1. `1-canonicalize-requests-and-responses`
2. `2-evaluate-freshness-and-stale-policy`
3. `3-merge-conditional-304-responses`
4. `4-apply-invalidation-rules`
5. `5-integrated-cache-audit-and-recovery`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
43 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://www.rfc-editor.org/rfc/rfc9111 (IETF Trust Legal Provisions); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
