# Atomic Filesystem Manifest Installer

`mini-posix-manifest-installer` is a five-step, offline Greenfield terminal benchmark candidate in
the `filesystem deployment and rollback` domain.

The five cumulative Steps are:

1. `1-validate-deployment-manifest`
2. `2-plan-atomic-install-operations`
3. `3-write-and-replay-intent-records`
4. `4-plan-rollback-from-manifest`
5. `5-integrated-safe-install-audit`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
36 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html (Open Group Base Specifications Issue 7 terms); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
