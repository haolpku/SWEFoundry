"""Public value objects used by the offline DNS zone auditor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple


@dataclass(frozen=True, order=True)
class DnsRecord:
    owner: str
    type: str
    ttl: int
    data: Tuple[str, ...]


@dataclass(frozen=True, order=True)
class ZoneProblem:
    owner: str
    severity: str
    type: str
    message: str


@dataclass(frozen=True)
class DnsAnswer:
    qname: str
    qtype: str
    rcode: str
    answers: Tuple[DnsRecord, ...]
    chain: Tuple[str, ...]


@dataclass(frozen=True)
class ZoneMigration:
    target_ttl: int
    records: Tuple[DnsRecord, ...]
    changes: Tuple[str, ...]
    digests: Mapping[str, str]


@dataclass(frozen=True)
class ZoneAuditReport:
    origin: str
    records: Tuple[DnsRecord, ...]
    problems: Tuple[ZoneProblem, ...]
    answers: Tuple[DnsAnswer, ...]
    migration: ZoneMigration
    recovery: Mapping[str, str]
