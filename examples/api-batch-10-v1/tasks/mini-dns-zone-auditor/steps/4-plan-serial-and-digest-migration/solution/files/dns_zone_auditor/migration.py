"""Deterministic, non-mutating DNS zone migration planning."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from types import MappingProxyType

from .models import DnsRecord, ZoneMigration


def _canonical_records(records: list[DnsRecord]) -> list[DnsRecord]:
    return sorted(records, key=lambda r: (r.owner, r.type, r.data, r.ttl))


def _line(record: DnsRecord) -> str:
    return "|".join((record.owner, record.type, str(record.ttl), *record.data))


def _digest(record_set: list[DnsRecord]) -> str:
    payload = "\n".join(_line(r) for r in _canonical_records(record_set)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def plan_zone_migration(records: list[DnsRecord], target_ttl: int) -> ZoneMigration:
    if target_ttl < 0:
        raise ValueError("target_ttl must be non-negative")
    changed: list[DnsRecord] = []
    changes: list[str] = []
    for record in _canonical_records(records):
        ttl = target_ttl
        data = record.data
        if record.type == "SOA":
            serial = int(record.data[2]) + 1
            data = (record.data[0], record.data[1], str(serial), record.data[3], record.data[4], record.data[5], record.data[6])
            if serial != int(record.data[2]):
                changes.append(f"{record.owner} SOA serial {record.data[2]} -> {serial}")
        if record.ttl != target_ttl:
            changes.append(f"{record.owner} {record.type} ttl {record.ttl} -> {target_ttl}")
        changed.append(DnsRecord(record.owner, record.type, ttl, data))
    grouped: dict[str, list[DnsRecord]] = defaultdict(list)
    for record in changed:
        grouped[f"{record.owner} {record.type}"].append(record)
    digests = {key: _digest(value) for key, value in sorted(grouped.items())}
    if len(changed) == len(records) and all(a == b for a, b in zip(_canonical_records(records), changed)):
        changes = []
    return ZoneMigration(target_ttl, tuple(changed), tuple(sorted(changes)), MappingProxyType(digests))
