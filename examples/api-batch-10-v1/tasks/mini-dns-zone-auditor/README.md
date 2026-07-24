# Offline DNS Zone Parser and Delegation Integrity Auditor

`mini-dns-zone-auditor` is a five-step, offline Greenfield terminal benchmark candidate in
the `network protocol data format` domain.

The five cumulative Steps are:

1. `1-parse-zone-master-files`
2. `2-validate-zone-integrity`
3. `3-simulate-offline-dns-answers`
4. `4-plan-serial-and-digest-migration`
5. `5-integrated-zone-audit`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
43 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://www.rfc-editor.org/rfc/rfc1035 (IETF Trust Legal Provisions); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
