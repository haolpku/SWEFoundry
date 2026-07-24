"""Deterministic offline POSIX-style manifest installer benchmark package."""

from .exceptions import ManifestError, RecoveryError
from .installer import (
    InstallAuditReport,
    InstallOp,
    ManifestEntry,
    RollbackPlan,
    audit_install,
    load_deploy_manifest,
    plan_install,
    plan_rollback,
    replay_intent_log,
    write_intent_log,
)

__all__ = [
    "InstallAuditReport",
    "InstallOp",
    "ManifestEntry",
    "ManifestError",
    "RecoveryError",
    "RollbackPlan",
    "audit_install",
    "load_deploy_manifest",
    "plan_install",
    "plan_rollback",
    "replay_intent_log",
    "write_intent_log",
]
