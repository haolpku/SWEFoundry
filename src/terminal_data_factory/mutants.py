from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MutationRule:
    name: str
    path: str
    find: str
    replace: str


@dataclass(frozen=True)
class MutantArtifact:
    mutant_id: str
    rule: str
    source_path: str
    output_path: str
    sha256: str


def generate_mutants(task_root: Path, rules: list[MutationRule], output_root: Path) -> list[MutantArtifact]:
    artifacts: list[MutantArtifact] = []
    output_root.mkdir(parents=True, exist_ok=True)
    for position, rule in enumerate(rules, 1):
        source = task_root / rule.path
        if not source.is_file():
            raise FileNotFoundError(source)
        text = source.read_text(encoding="utf-8")
        occurrences = text.count(rule.find)
        if occurrences != 1:
            raise ValueError(f"{rule.name}: expected one match, found {occurrences}")
        mutated = text.replace(rule.find, rule.replace, 1)
        mutant_id = f"m{position:03d}-{rule.name}"
        destination = output_root / mutant_id / rule.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(mutated, encoding="utf-8")
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        artifacts.append(MutantArtifact(mutant_id, rule.name, rule.path, destination.relative_to(output_root).as_posix(), f"sha256:{digest}"))
    (output_root / "manifest.json").write_text(
        json.dumps({"schema_version": "mutants-v1", "mutants": [asdict(item) for item in artifacts]}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifacts


def load_rules(path: Path) -> list[MutationRule]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return [MutationRule(**item) for item in value["rules"]]
