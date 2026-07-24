from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .core import (
    Artifact,
    Operator,
    OperatorContext,
    OperatorOutput,
    atomic_json,
    sha256_json,
)


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root
        self.artifacts = root / "artifacts"
        self.cache = root / "cache"
        self.runs = root / "runs"

    def put(
        self,
        artifact_type: str,
        artifact_version: str,
        producer: str,
        parents: tuple[str, ...],
        data: Any,
    ) -> Artifact:
        content = {
            "artifact_type": artifact_type,
            "artifact_version": artifact_version,
            "producer": producer,
            "parents": list(parents),
            "data": data,
        }
        digest = sha256_json(content)
        artifact = Artifact(
            digest=digest,
            artifact_type=artifact_type,
            artifact_version=artifact_version,
            producer=producer,
            parents=parents,
            data=data,
        )
        path = self.artifacts / digest[:2] / f"{digest}.json"
        if not path.exists():
            atomic_json(path, artifact.envelope())
        return artifact

    def get(self, digest: str) -> Artifact:
        path = self.artifacts / digest[:2] / f"{digest}.json"
        raw = json.loads(path.read_text())
        if raw["digest"] != digest:
            raise ValueError(f"artifact digest mismatch: {digest}")
        content = {
            "artifact_type": raw["artifact_type"],
            "artifact_version": raw["artifact_version"],
            "producer": raw["producer"],
            "parents": raw["parents"],
            "data": raw["data"],
        }
        actual = sha256_json(content)
        if actual != digest:
            raise ValueError(
                f"artifact content was modified: expected {digest}, got {actual}"
            )
        return Artifact(
            digest=raw["digest"],
            artifact_type=raw["artifact_type"],
            artifact_version=raw["artifact_version"],
            producer=raw["producer"],
            parents=tuple(raw["parents"]),
            data=raw["data"],
        )

    def cache_get(self, key: str) -> dict[str, str] | None:
        path = self.cache / f"{key}.json"
        return json.loads(path.read_text()) if path.is_file() else None

    def cache_put(self, key: str, outputs: Mapping[str, Artifact]) -> None:
        atomic_json(
            self.cache / f"{key}.json",
            {name: artifact.digest for name, artifact in sorted(outputs.items())},
        )


class PipelineRuntime:
    def __init__(
        self,
        store: ArtifactStore,
        operators: Mapping[str, Operator],
    ):
        self.store = store
        self.operators = dict(operators)

    def run(self, pipeline_path: Path) -> dict[str, Any]:
        pipeline_path = pipeline_path.resolve()
        spec = json.loads(pipeline_path.read_text())
        if spec.get("schema_version") != "1.0":
            raise ValueError("pipeline schema_version must be 1.0")
        nodes = spec.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("pipeline requires non-empty nodes")
        run_id = spec.get("run_id") or f"run-{sha256_json(spec)[:16]}"
        context = OperatorContext(
            pipeline_path=pipeline_path,
            workspace=self.store.root,
        )
        node_outputs: dict[str, dict[str, Artifact]] = {}
        events: list[dict[str, Any]] = []
        cache_hits = 0

        for sequence, node in enumerate(nodes, 1):
            node_id = str(node["id"])
            if node_id in node_outputs:
                raise ValueError(f"duplicate pipeline node id: {node_id}")
            operator_name = str(node["operator"])
            if operator_name not in self.operators:
                raise KeyError(f"unknown operator: {operator_name}")
            operator = self.operators[operator_name]
            inputs: dict[str, Artifact] = {}
            for input_name, reference in sorted(
                (node.get("inputs") or {}).items()
            ):
                source_node, separator, output_name = str(reference).partition(".")
                if not separator or source_node not in node_outputs:
                    raise ValueError(
                        f"{node_id}.{input_name}: invalid reference {reference}"
                    )
                if output_name not in node_outputs[source_node]:
                    raise ValueError(
                        f"{node_id}.{input_name}: unknown output {reference}"
                    )
                inputs[input_name] = node_outputs[source_node][output_name]
            operator.validate_inputs(inputs)
            config = node.get("config") or {}
            cache_key = sha256_json(
                {
                    "operator": operator.name,
                    "version": operator.version,
                    "config": operator.fingerprint(context, config),
                    "inputs": {
                        name: artifact.digest
                        for name, artifact in sorted(inputs.items())
                    },
                }
            )
            cached = self.store.cache_get(cache_key)
            if cached:
                outputs = {
                    name: self.store.get(digest)
                    for name, digest in cached.items()
                }
                operator.validate_outputs(
                    {
                        name: OperatorOutput(
                            artifact_type=artifact.artifact_type,
                            artifact_version=artifact.artifact_version,
                            data=None,
                        )
                        for name, artifact in outputs.items()
                    }
                )
                cache_hit = True
                cache_hits += 1
            else:
                raw_outputs = operator.run(context, inputs, config)
                operator.validate_outputs(raw_outputs)
                parents = tuple(
                    artifact.digest
                    for _, artifact in sorted(inputs.items())
                )
                outputs = {
                    name: self.store.put(
                        artifact_type=output.artifact_type,
                        artifact_version=output.artifact_version,
                        producer=f"{operator.name}@{operator.version}",
                        parents=parents,
                        data=output.data,
                    )
                    for name, output in sorted(raw_outputs.items())
                }
                self.store.cache_put(cache_key, outputs)
                cache_hit = False
            node_outputs[node_id] = outputs
            events.append(
                {
                    "sequence": sequence,
                    "node_id": node_id,
                    "operator": operator.name,
                    "operator_version": operator.version,
                    "cache_hit": cache_hit,
                    "inputs": {
                        name: artifact.digest
                        for name, artifact in sorted(inputs.items())
                    },
                    "outputs": {
                        name: artifact.digest
                        for name, artifact in sorted(outputs.items())
                    },
                }
            )

        summary = {
            "schema_version": "1.0",
            "run_id": run_id,
            "pipeline_digest": sha256_json(spec),
            "status": "completed",
            "nodes": len(nodes),
            "cache_hits": cache_hits,
            "events": events,
            "outputs": {
                node_id: {
                    name: artifact.digest
                    for name, artifact in sorted(outputs.items())
                }
                for node_id, outputs in node_outputs.items()
            },
        }
        atomic_json(self.store.runs / run_id / "run.json", summary)
        return summary
