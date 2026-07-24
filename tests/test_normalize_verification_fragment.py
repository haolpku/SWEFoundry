from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from normalize_verification_fragment import normalize_payload  # noqa: E402


def item(path: str, content: str, executable: bool = False) -> dict:
    return {"path": path, "content": content, "executable": executable}


def test_normalizer_moves_mutants_and_repairs_audit_and_step_shell() -> None:
    payload = {
        "schema_version": "1.0",
        "task_id": "mini-example",
        "fragment": "verification",
        "files": [
            item("mutants/fp1_fault.py", "FAULT = 1", True),
            item(
                "verifier/run_audit.py",
                """#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MUTANTS = ROOT / "mutants"
direct = ROOT / "verifier" / "fp1_fault.py"
already_under_verifier = ROOT / "verifier" / "mutants" / "fp1_fault.py"
dynamic = ROOT / "verifier" / mutant
report = {"all_passed": True}
raise SystemExit(0 if report["all_passed"] else 1)
for rel in ["environment/codebase", "steps", "verifier", "mutants"]:
    print(rel)
""",
                True,
            ),
            item("steps/1-stage/instruction.md", "Implement the stage."),
            item(
                "steps/1-stage/tests/test.sh",
                '#!/bin/sh\npython3 "$TDF_TESTS_DIR/verifier.py"\n',
                True,
            ),
        ],
    }
    normalized, changed_paths, content_changes = normalize_payload(payload)
    files = {entry["path"]: entry["content"] for entry in normalized["files"]}
    assert "verifier/anti_cheat/fp1_fault.py" in files
    audit = files["verifier/run_audit.py"]
    ast.parse(audit)
    assert "ROOT / 'verifier' / 'anti_cheat'" in audit
    assert "ROOT / 'verifier' / 'anti_cheat' / mutant" in audit
    assert "'passed': True" in audit
    assert "report['passed']" in audit
    assert "'verifier' / 'verifier'" not in audit
    assert "['environment/codebase', 'steps', 'verifier']" in audit
    shell = files["steps/1-stage/tests/test.sh"]
    assert (
        'env -u PYTHONPATH -u PYTHONHOME python3 -I "$TDF_TESTS_DIR/verifier.py"'
        in shell
    )
    instruction = files["steps/1-stage/instruction.md"]
    assert "/app/knowledge/public_api.md" in instruction
    assert "python public_contract_tests/step_01_smoke.py" in instruction
    assert changed_paths
    assert (
        "audit-mutant-paths-and-schema:verifier/run_audit.py" in content_changes
    )


def test_normalizer_moves_exec_before_env_assignments() -> None:
    payload = {
        "schema_version": "1.0",
        "task_id": "mini-example",
        "fragment": "verification",
        "files": [
            item(
                "steps/1-stage/tests/test.sh",
                (
                    "#!/bin/sh\n"
                    'PYTHONDONTWRITEBYTECODE=1 TDF_WORKSPACE="$ROOT" '
                    'exec python3 "$TESTS/verifier.py"\n'
                ),
                True,
            )
        ],
    }
    normalized, _, _ = normalize_payload(payload)
    shell = normalized["files"][0]["content"]
    assert (
        'exec env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 '
        'TDF_WORKSPACE="$ROOT" python3 -I "$TESTS/verifier.py"'
    ) in shell
