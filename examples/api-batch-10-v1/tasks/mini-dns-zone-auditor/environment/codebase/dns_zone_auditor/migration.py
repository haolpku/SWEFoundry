"""Starter migration planner."""
from __future__ import annotations

from .models import DnsRecord, ZoneMigration


def plan_zone_migration(records: list[DnsRecord], target_ttl: int) -> ZoneMigration:
    return ZoneMigration(target_ttl, tuple(records), tuple(), {})
