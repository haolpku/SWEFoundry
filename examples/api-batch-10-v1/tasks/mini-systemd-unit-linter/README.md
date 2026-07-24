# Systemd Unit Dependency Linter and Boot Plan Simulator

`mini-systemd-unit-linter` is a five-step, offline Greenfield terminal benchmark candidate in
the `process supervision and service configuration` domain.

The five cumulative Steps are:

1. `1-parse-unit-files-deterministically`
2. `2-validate-dependency-integrity`
3. `3-compute-boot-activation-order`
4. `4-replay-failure-recovery`
5. `5-integrated-unit-audit`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
38 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://github.com/systemd/systemd (LGPL-2.1-or-later); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
