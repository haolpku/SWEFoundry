# PNG Asset Integrity and Deterministic Transcoding Planner

`mini-png-asset-pipeline` is a five-step, offline Greenfield terminal benchmark candidate in
the `media processing` domain.

The five cumulative Steps are:

1. `1-parse-png-chunks`
2. `2-verify-crc-and-chunk-invariants`
3. `3-extract-deterministic-asset-metadata`
4. `4-plan-deterministic-png-cleanup`
5. `5-integrated-png-audit`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
43 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://www.w3.org/TR/png/ (W3C Document License); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
