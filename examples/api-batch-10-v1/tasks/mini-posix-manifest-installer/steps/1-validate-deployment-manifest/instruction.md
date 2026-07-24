Step 1 verification: validate deployment manifest.

Required public API: class ManifestEntry and load_deploy_manifest(path: str) -> list[ManifestEntry].

Disclosed hidden behavioral names for this step: path normalization, duplicate destination detection, canonical ordering. Deterministic fault protected by fp1_allows_traversal: accepts destinations containing normalized parent directory traversal.

The verifier is black-box: it imports only the installed public package in isolated Python subprocesses and never reads candidate source.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_01_smoke.py`.
