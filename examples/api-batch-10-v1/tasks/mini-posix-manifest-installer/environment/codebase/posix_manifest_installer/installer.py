"""Starter implementation for a deterministic manifest installer.

This file is intentionally useful but incomplete. The step solutions replace it
with progressively complete implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
import posixpath
from typing import Any

from .exceptions import RecoveryError


@dataclass(frozen=True)
class ManifestEntry:
    source: str
    destination: str
    sha256: str


@dataclass(frozen=True)
class InstallOp:
    op_id: str
    destination: str
    source: str
    sha256: str
    temp_path: str
    backup_path: str | None
    previous_sha256: str | None
    action: str = "install"
    directories: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RollbackPlan:
    actions: tuple[dict[str, Any], ...]
    errors: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class InstallAuditReport:
    recovered_operation_ids: tuple[str, ...]
    install_operations: tuple[InstallOp, ...]
    rollback_plan: RollbackPlan


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_destination(value: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError("destination must be a non-empty string")
    if value.startswith("/"):
        raise ValueError("destination must be relative")
    normalized = posixpath.normpath(value)
    if normalized == ".":
        raise ValueError("destination must name a file")
    return normalized


def load_deploy_manifest(path: str) -> list[ManifestEntry]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    rows = data.get("files") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("manifest must be a list or contain a files list")
    base = os.path.dirname(os.path.abspath(path))
    entries: list[ManifestEntry] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("manifest entries must be objects")
        destination = _normalize_destination(row.get("destination"))
        if destination in seen:
            raise ValueError(f"duplicate destination: {destination}")
        seen.add(destination)
        source_value = row.get("source")
        sha256 = row.get("sha256")
        if not isinstance(source_value, str) or source_value == "":
            raise ValueError("source must be a non-empty string")
        if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        source = source_value if os.path.isabs(source_value) else os.path.normpath(os.path.join(base, source_value))
        entries.append(ManifestEntry(source=source, destination=destination, sha256=sha256))
    return sorted(entries, key=lambda entry: entry.destination)


def plan_install(root: str, entries: list[ManifestEntry]) -> list[InstallOp]:
    raise NotImplementedError("step 2 implements installation planning")


def write_intent_log(path: str, ops: list[InstallOp]) -> None:
    raise NotImplementedError("step 3 implements intent log writing")


def replay_intent_log(root: str, log_path: str) -> list[str]:
    raise NotImplementedError("step 3 implements intent replay")


def plan_rollback(root: str, log_path: str) -> RollbackPlan:
    raise NotImplementedError("step 4 implements rollback planning")


def audit_install(root: str, manifest_path: str, log_path: str) -> InstallAuditReport:
    raise NotImplementedError("step 5 implements integrated audit")
