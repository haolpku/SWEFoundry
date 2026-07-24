"""Read-only deterministic validation for parsed DNS zones."""
from __future__ import annotations

from collections import defaultdict

from .models import DnsRecord, ZoneProblem

_SEVERITY_RANK = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def _sort_problem(problem: ZoneProblem) -> tuple[str, int, str, str]:
    return (problem.owner, _SEVERITY_RANK.get(problem.severity, 9), problem.type, problem.message)


def _apex(records: list[DnsRecord]) -> str:
    if not records:
        return "."
    soa = sorted(r.owner for r in records if r.type == "SOA")
    labels = [record.owner.rstrip(".").split(".") for record in records]
    common: list[str] = []
    for group in zip(*(reversed(item) for item in labels)):
        if len(set(group)) != 1:
            break
        common.append(group[0])
    common_owner = ".".join(reversed(common)) + "." if common else "."
    # A meaningful multi-label common suffix distinguishes a misplaced SOA
    # from the surrounding zone without requiring an undisclosed origin input.
    if soa and len(common) >= 2 and soa[0] != common_owner:
        return common_owner
    if soa:
        return soa[0]
    return common_owner


def validate_zone(records: list[DnsRecord]) -> list[ZoneProblem]:
    problems: list[ZoneProblem] = []
    apex = _apex(records)
    by_owner: dict[str, list[DnsRecord]] = defaultdict(list)
    seen: dict[DnsRecord, int] = defaultdict(int)
    for record in records:
        by_owner[record.owner].append(record)
        seen[record] += 1
    soa = [r for r in records if r.type == "SOA"]
    if len(soa) != 1:
        problems.append(ZoneProblem(apex, "ERROR", "SOA_COUNT", "zone must contain exactly one SOA record"))
    elif soa[0].owner != apex:
        problems.append(ZoneProblem(soa[0].owner, "ERROR", "SOA_APEX", "SOA record must be at the zone apex"))
    if not any(r.owner == apex and r.type == "NS" for r in records):
        problems.append(ZoneProblem(apex, "ERROR", "APEX_NS_MISSING", "zone apex must contain at least one NS record"))
    for owner, owner_records in by_owner.items():
        types = {r.type for r in owner_records}
        if "CNAME" in types and len(types) > 1:
            problems.append(ZoneProblem(owner, "ERROR", "CNAME_EXCLUSIVE", "CNAME owner must not have other record types"))
        cname_count = sum(1 for r in owner_records if r.type == "CNAME")
        if cname_count > 1:
            problems.append(ZoneProblem(owner, "ERROR", "CNAME_MULTIPLE", "owner must not have multiple CNAME records"))
    for record, count in seen.items():
        if count > 1:
            problems.append(ZoneProblem(record.owner, "ERROR", "DUPLICATE_RR", f"duplicate {record.type} record"))
    address_owners = {r.owner for r in records if r.type in {"A", "AAAA"}}
    for ns in records:
        if ns.type == "NS" and ns.owner != apex:
            target = ns.data[0]
            if target.endswith(ns.owner) and target not in address_owners:
                problems.append(ZoneProblem(target, "WARNING", "GLUE_MISSING", "in-bailiwick delegation target needs address glue"))
    return sorted(problems, key=_sort_problem)
