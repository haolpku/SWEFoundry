from __future__ import annotations

from pathlib import Path

from ..records import TaskRecord
from .base import FamilyDescriptor, TaskFamily, common_profile
from .nl2repo import NL2RepoFamily
from .swe_bench import SWEBenchFamily
from .terminal_bench import TerminalBenchFamily


class DescriptorOnlyFamily:
    def __init__(self, descriptor: FamilyDescriptor) -> None:
        self.descriptor = descriptor

    def import_records(self, source: Path, *, source_ref: str, dataset_version: str) -> list[TaskRecord]:
        raise NotImplementedError(f"{self.descriptor.family_id} importer is planned but not implemented")

    def validate_record(self, record: TaskRecord) -> list[str]:
        return common_profile(record)

    def package_for_harbor(self, source: Path, output: Path, *, source_ref: str, dataset_version: str) -> list[Path]:
        raise NotImplementedError(f"{self.descriptor.family_id} Harbor packaging is planned but not implemented")


def builtin_families() -> dict[str, TaskFamily]:
    families: list[TaskFamily] = [
        TerminalBenchFamily(),
        SWEBenchFamily(),
        NL2RepoFamily(),
        DescriptorOnlyFamily(FamilyDescriptor(
            "deep-swe", "original long-horizon repository engineering", False, False,
            "P1", "medium_to_high",
        )),
        DescriptorOnlyFamily(FamilyDescriptor(
            "frontier-swe", "ultra-long implementation, performance, and research", False, False,
            "P2", "high",
        )),
    ]
    return {family.descriptor.family_id: family for family in families}


def get_family(family_id: str) -> TaskFamily:
    try:
        return builtin_families()[family_id]
    except KeyError as exc:
        choices = ", ".join(sorted(builtin_families()))
        raise ValueError(f"unknown family {family_id!r}; choose one of: {choices}") from exc
