"""Starter integrated audit."""
from __future__ import annotations

from .migration import plan_zone_migration
from .models import DnsAnswer, ZoneAuditReport
from .parser import parse_zone
from .validators import validate_zone


def audit_zone(text: str, origin: str, queries: list[tuple[str, str]], target_ttl: int) -> ZoneAuditReport:
    records = tuple(parse_zone(text, origin))
    problems = tuple(validate_zone(list(records)))
    migration = plan_zone_migration(list(records), target_ttl)
    return ZoneAuditReport(origin if origin.endswith(".") else origin + ".", records, problems, tuple(), migration, {"status": "starter"})
