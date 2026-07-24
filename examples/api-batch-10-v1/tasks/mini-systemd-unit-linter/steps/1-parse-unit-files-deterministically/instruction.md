# Step 1 verification contract

Parse restricted systemd unit files deterministically. The verifier is black-box and checks these disclosed names: canonical_unit_names_sorted, comment_handling_and_section_semantics, duplicate_scalar_key_rejected, malformed_section_header_rejected, duplicate_normalized_unit_name_rejected, file_path_input_supported, read_only_state_check.

Expected public API: class UnitFile and def load_units(paths: list[str]) -> list[UnitFile].

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_01_smoke.py`.
