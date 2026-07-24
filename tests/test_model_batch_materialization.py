from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from materialize_model_batch import materialize_batch  # noqa: E402
from materialize_model_bundle import validate_bundle  # noqa: E402
from merge_model_fragments import merge_fragments  # noqa: E402


def valid_payload(task_id: str) -> dict:
    files = [
        {"path": path, "executable": path.endswith(".sh"), "content": "safe"}
        for path in (
            "README.md",
            "metadata.json",
            "task.toml",
            "environment/Dockerfile",
            "environment/knowledge/index.md",
            "environment/knowledge/public_api.md",
            "environment/knowledge/public_api.json",
            "verifier/run_audit.py",
        )
    ]
    for step in range(1, 6):
        root = f"steps/{step}-stage-{step}"
        files.extend(
            [
                {
                    "path": f"{root}/instruction.md",
                    "executable": False,
                    "content": f"step {step}",
                },
                {
                    "path": f"{root}/solution/solve.sh",
                    "executable": True,
                    "content": "#!/bin/sh\ntrue",
                },
                {
                    "path": f"{root}/tests/verifier.py",
                    "executable": False,
                    "content": "assert True",
                },
                {
                    "path": f"{root}/tests/test.sh",
                    "executable": True,
                    "content": "#!/bin/sh\ntrue",
                },
                {
                    "path": f"verifier/anti_cheat/fp{step}_step{step}_fault.py",
                    "executable": False,
                    "content": f"FAULT_STEP = {step}",
                },
            ]
        )
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "files": files,
        "known_open_gates": [],
    }


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_merge_fragments_infers_task_and_prevents_cross_task_mix(
    tmp_path: Path,
) -> None:
    fragments = []
    for name in ("core", "verification", "package"):
        fragments.append(
            write_json(
                tmp_path / f"{name}.json",
                {
                    "schema_version": "1.0",
                    "task_id": "mini-safe-ledger",
                    "fragment": name,
                    "files": [
                        {
                            "path": f"{name}.txt",
                            "executable": False,
                            "content": name,
                        }
                    ],
                },
            )
        )
    merged = merge_fragments(fragments)
    assert merged["task_id"] == "mini-safe-ledger"
    assert merged["fragments"] == ["core", "package", "verification"]

    wrong = json.loads(fragments[-1].read_text())
    wrong["task_id"] = "mini-other-ledger"
    fragments[-1].write_text(json.dumps(wrong))
    with pytest.raises(ValueError, match="does not match"):
        merge_fragments(fragments)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("sk-" + "abcdefghijklmnopqrstuv", "secret-like"),
        ("http://" + "192.0.2.1:3000/v1", "endpoint"),
        ("/Users/" + "example/private/file", "host absolute"),
    ],
)
def test_bundle_rejects_sensitive_content(content: str, message: str) -> None:
    payload = valid_payload("mini-safe-ledger")
    payload["files"][0]["content"] = content
    with pytest.raises(ValueError, match=message):
        validate_bundle(payload)


def test_bundle_rejects_secret_hidden_in_top_level_notes() -> None:
    payload = valid_payload("mini-safe-ledger")
    payload["implementation_notes"] = ["Authorization: Bearer abcdefghijklmnopqrst"]
    with pytest.raises(ValueError, match="secret-like"):
        validate_bundle(payload)


def test_bundle_requires_five_steps_and_one_mutant_per_step() -> None:
    payload = valid_payload("mini-safe-ledger")
    payload["files"] = [
        item
        for item in payload["files"]
        if item["path"] != "verifier/anti_cheat/fp5_step5_fault.py"
    ]
    payload["files"].append(
        {
            "path": "verifier/anti_cheat/extra.py",
            "executable": False,
            "content": "safe",
        }
    )
    with pytest.raises(ValueError, match="does not identify step"):
        validate_bundle(payload)


def test_batch_materializes_ten_unique_tasks_transactionally(
    tmp_path: Path,
) -> None:
    paths = [
        write_json(tmp_path / f"bundle-{index}.json", valid_payload(f"mini-batch-{index}"))
        for index in range(10)
    ]
    output = tmp_path / "tasks"
    manifest = materialize_batch(paths, output)
    assert manifest["task_count"] == 10
    assert len(list(output.glob("mini-batch-*"))) == 10
    assert (output / "BATCH_MANIFEST.json").exists()


def test_batch_rejects_duplicate_task_without_partial_output(
    tmp_path: Path,
) -> None:
    paths = [
        write_json(
            tmp_path / f"bundle-{index}.json",
            valid_payload("mini-duplicate" if index in (0, 9) else f"mini-batch-{index}"),
        )
        for index in range(10)
    ]
    output = tmp_path / "tasks"
    with pytest.raises(ValueError, match="duplicate task ids"):
        materialize_batch(paths, output)
    assert not output.exists()
