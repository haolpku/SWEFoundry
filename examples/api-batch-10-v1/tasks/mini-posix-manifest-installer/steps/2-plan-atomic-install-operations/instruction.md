Step 2 verification: read-only atomic install planning.

Required public API: class ManifestEntry, class InstallOp, load_deploy_manifest, and plan_install(root: str, entries: list[ManifestEntry]) -> list[InstallOp].

Disclosed hidden behavioral names for this step: digest integrity, directory creation ordering, read-only planning. Deterministic fault protected by fp2_mtime_comparison: uses file metadata instead of declared sha256 content digest to decide whether a file is unchanged.

The verifier is black-box: it imports only the installed public package in isolated Python subprocesses and never reads candidate source.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_02_smoke.py`.
