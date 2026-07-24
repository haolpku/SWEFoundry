"""Offline DNS zone auditor educational package."""
from .models import DnsAnswer, DnsRecord, ZoneAuditReport, ZoneMigration, ZoneProblem
from .parser import parse_zone
from .validators import validate_zone
from .resolver import answer_zone
from .migration import plan_zone_migration
from .audit import audit_zone
from .exceptions import DnsZoneError, ZoneParseError, ZoneValidationError

__all__ = [
    "DnsAnswer",
    "DnsRecord",
    "ZoneAuditReport",
    "ZoneMigration",
    "ZoneProblem",
    "parse_zone",
    "validate_zone",
    "answer_zone",
    "plan_zone_migration",
    "audit_zone",
    "DnsZoneError",
    "ZoneParseError",
    "ZoneValidationError",
]
