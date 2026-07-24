from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from terminal_data_factory.operators import (
    ArtifactStore,
    PipelineRuntime,
    builtin_registry,
)
from terminal_data_factory.operators.core import Artifact, OperatorContext
from terminal_data_factory.operators.builtin import (
    DesignMultistepOperator,
    QualityGateOperator,
    RolloutPlanOperator,
)


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "data_infra/pipelines/topic_to_calibration.json"
SOURCES = ROOT / "data_infra/inputs/topic_sources.json"


def artifact(artifact_type: str, data: object) -> Artifact:
    return Artifact(
        digest="test",
        artifact_type=artifact_type,
        artifact_version="1.0",
        producer="test",
        parents=(),
        data=data,
    )


def load_valid_blueprint() -> dict:
    source = json.loads(SOURCES.read_text())[0]
    topics = artifact(
        "selected-topics",
        {"topics": [{**source, "topic_id": source["id"]}], "count": 1},
    )
    context = OperatorContext(PIPELINE, ROOT)
    result = DesignMultistepOperator().run(context, {"topics": topics}, {})
    return result["blueprints"].data["blueprints"][0]


def test_example_pipeline_is_deterministic_and_cached(tmp_path: Path) -> None:
    runtime = PipelineRuntime(ArtifactStore(tmp_path), builtin_registry())

    first = runtime.run(PIPELINE)
    second = runtime.run(PIPELINE)

    assert first["nodes"] == 10
    assert first["cache_hits"] == 0
    assert second["cache_hits"] == 10
    assert first["outputs"] == second["outputs"]

    def output_data(node: str, output: str) -> dict:
        return runtime.store.get(first["outputs"][node][output]).data

    assert output_data("find_topics", "candidates")["count"] == 1
    assert output_data("find_topics", "rejected")["count"] == 1
    assert output_data("quality_gate", "accepted")["count"] == 1
    assert output_data("plan_mutants", "plan")["count"] == 5
    assert output_data("plan_mutants", "plan")["covers_final_step"] is True
    assert output_data("rollout_plan", "plan")["job_count"] == 6
    assert output_data("package_plan", "plan")["count"] == 1


def test_quality_gate_rejects_nondeterministic_mutant() -> None:
    blueprint = copy.deepcopy(load_valid_blueprint())
    blueprint["steps"][4]["mutant"]["deterministic_fault"] = (
        "return hash(key) modulo the partition count"
    )
    result = QualityGateOperator().run(
        OperatorContext(PIPELINE, ROOT),
        {
            "blueprints": artifact(
                "task-blueprints",
                {"blueprints": [blueprint], "count": 1},
            )
        },
        {},
    )

    assert result["accepted"].data["count"] == 0
    assert "step 5: nondeterministic mutant" in (
        result["report"].data["reports"][0]["errors"]
    )


def test_rollout_plan_requires_independent_model_families() -> None:
    with pytest.raises(ValueError, match="at least two model families"):
        RolloutPlanOperator().run(
            OperatorContext(PIPELINE, ROOT),
            {
                "blueprints": artifact(
                    "accepted-blueprints",
                    {"blueprints": [], "count": 0},
                )
            },
            {"model_families": [{"family": "gpt", "model": "gpt-target"}]},
        )


def test_artifact_store_detects_content_tampering(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    created = store.put("example", "1.0", "test", (), {"value": 1})
    path = store.artifacts / created.digest[:2] / f"{created.digest}.json"
    raw = json.loads(path.read_text())
    raw["data"]["value"] = 2
    path.write_text(json.dumps(raw))

    with pytest.raises(ValueError, match="content was modified"):
        store.get(created.digest)
