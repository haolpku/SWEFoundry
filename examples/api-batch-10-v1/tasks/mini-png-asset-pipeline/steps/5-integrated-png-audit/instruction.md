# Step 5: Integrated PNG audit

Implement `class PngAuditReport` and `audit_png(data: bytes) -> PngAuditReport`.

The verifier discloses these required behavioral names: valid_audit_preserves_all_outputs, corrupt_ancillary_integrates_crc_and_cleanup, truncated_write_recovery_guidance, metadata_error_becomes_problem_not_exception, step1_regression_trailing_iend_rejected, step2_regression_idat_before_ihdr_reported, step3_regression_canonical_metadata_order, step4_regression_critical_crc_cannot_remove, and read_only_state_check.

Integrated audit is read-only. It must preserve parser, validator, metadata, and cleanup outputs; convert parse failures into `PARSE_ERROR` reports; convert metadata failures into `METADATA_ERROR` problems; and provide deterministic recovery/migration guidance including discarding incomplete candidates, same-directory temporary writes, fsync, and atomic `os.replace` publication.

## Public contract

Read `/app/knowledge/public_api.md`, then run the disclosed smoke test from `/app/workspace`:

```sh
python public_contract_tests/step_05_smoke.py
```
