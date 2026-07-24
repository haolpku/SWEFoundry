"""Integrated deterministic read-only zone audit."""
from __future__ import annotations

import hashlib
from types import MappingProxyType

from .migration import plan_zone_migration
from .models import DnsAnswer, DnsRecord, ZoneAuditReport, ZoneProblem
from .parser import parse_zone
from .resolver import answer_zone
from .validators import validate_zone


def _canon_origin(origin: str) -> str:
    return (origin if origin.endswith(".") else origin + ".").lower()


def _record_line(record: DnsRecord) -> str:
    return "|".join((record.owner, record.type, str(record.ttl), *record.data))


def _problem_line(problem: ZoneProblem) -> str:
    return "|".join((problem.owner, problem.severity, problem.type, problem.message))


def _answer_line(answer: DnsAnswer) -> str:
    rr = ";".join(_record_line(record) for record in answer.answers)
    chain = ">".join(answer.chain)
    return "|".join((answer.qname, answer.qtype, answer.rcode, chain, rr))


def _sha256(lines: list[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def audit_zone(text: str, origin: str, queries: list[tuple[str, str]], target_ttl: int) -> ZoneAuditReport:
    canonical_origin = _canon_origin(origin)
    records = tuple(parse_zone(text, canonical_origin))
    problems = tuple(validate_zone(list(records)))
    answers = tuple(answer_zone(list(records), qname, qtype) for qname, qtype in queries)
    migration = plan_zone_migration(list(records), target_ttl)
    recovery = {
        "origin": canonical_origin,
        "record_count": str(len(records)),
        "problem_count": str(len(problems)),
        "answer_count": str(len(answers)),
        "records_sha256": _sha256([_record_line(r) for r in records]),
        "problems_sha256": _sha256([_problem_line(p) for p in problems]),
        "answers_sha256": _sha256([_answer_line(a) for a in answers]),
    }
    return ZoneAuditReport(canonical_origin, records, problems, answers, migration, MappingProxyType(recovery))
