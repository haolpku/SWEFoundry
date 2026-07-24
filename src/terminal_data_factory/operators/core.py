from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(canonical_json(value) + b"\n")
    os.replace(temporary, path)


@dataclass(frozen=True)
class Artifact:
    digest: str
    artifact_type: str
    artifact_version: str
    producer: str
    parents: tuple[str, ...]
    data: Any

    def envelope(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "digest": self.digest,
            "artifact_type": self.artifact_type,
            "artifact_version": self.artifact_version,
            "producer": self.producer,
            "parents": list(self.parents),
            "data": self.data,
        }


@dataclass(frozen=True)
class OperatorOutput:
    artifact_type: str
    data: Any
    artifact_version: str = "1.0"


@dataclass(frozen=True)
class OperatorContext:
    pipeline_path: Path
    workspace: Path

    def resolve(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (self.pipeline_path.parent / path)


class Operator:
    name = "operator"
    version = "1.0"
    input_types: Mapping[str, str] = {}
    output_types: Mapping[str, str] = {}

    def fingerprint(
        self,
        context: OperatorContext,
        config: Mapping[str, Any],
    ) -> Any:
        return config

    def validate_inputs(self, inputs: Mapping[str, Artifact]) -> None:
        missing = set(self.input_types) - set(inputs)
        extra = set(inputs) - set(self.input_types)
        if missing or extra:
            raise ValueError(
                f"{self.name}: input names differ; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        for name, expected in self.input_types.items():
            actual = inputs[name].artifact_type
            if actual != expected:
                raise TypeError(
                    f"{self.name}.{name}: expected {expected}, got {actual}"
                )

    def run(
        self,
        context: OperatorContext,
        inputs: Mapping[str, Artifact],
        config: Mapping[str, Any],
    ) -> Mapping[str, OperatorOutput]:
        raise NotImplementedError

    def validate_outputs(self, outputs: Mapping[str, OperatorOutput]) -> None:
        if set(outputs) != set(self.output_types):
            raise ValueError(
                f"{self.name}: outputs differ; expected "
                f"{sorted(self.output_types)}, got {sorted(outputs)}"
            )
        for name, expected in self.output_types.items():
            if outputs[name].artifact_type != expected:
                raise TypeError(
                    f"{self.name}.{name}: expected {expected}, "
                    f"got {outputs[name].artifact_type}"
                )
