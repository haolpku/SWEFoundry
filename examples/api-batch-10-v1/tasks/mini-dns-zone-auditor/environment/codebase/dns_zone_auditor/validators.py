"""Starter zone validation.

The complete step-2 behavior is supplied by the replacement solution.
"""
from __future__ import annotations

from .models import DnsRecord, ZoneProblem


def validate_zone(records: list[DnsRecord]) -> list[ZoneProblem]:
    problems: list[ZoneProblem] = []
    soa = [r for r in records if r.type == "SOA"]
    if len(soa) != 1:
        problems.append(ZoneProblem(".", "ERROR", "SOA_COUNT", "zone must contain exactly one SOA record"))
    return sorted(problems, key=lambda p: (p.owner, p.severity, p.type, p.message))
