"""Deterministic offline DNS answer simulation without sockets."""
from __future__ import annotations

from collections import defaultdict

from .models import DnsAnswer, DnsRecord

_SUPPORTED = {"SOA", "NS", "A", "AAAA", "CNAME", "TXT"}


def _canon(name: str) -> str:
    if not name:
        raise ValueError("qname is required")
    return (name if name.endswith(".") else name + ".").lower()


def _ordered(records: list[DnsRecord]) -> tuple[DnsRecord, ...]:
    return tuple(sorted(records, key=lambda r: (r.owner, r.type, r.data, r.ttl)))


def answer_zone(records: list[DnsRecord], qname: str, qtype: str) -> DnsAnswer:
    name = _canon(qname)
    typ = qtype.upper()
    if typ not in _SUPPORTED:
        raise ValueError(f"unsupported query type: {qtype}")
    by_owner: dict[str, list[DnsRecord]] = defaultdict(list)
    for record in records:
        by_owner[record.owner].append(record)
    current = name
    chain: list[str] = []
    answers: list[DnsRecord] = []
    seen: set[str] = set()
    limit = len(by_owner) + 1
    for _ in range(limit):
        chain.append(current)
        if current in seen:
            return DnsAnswer(name, typ, "CNAME_LOOP", _ordered(answers), tuple(chain))
        seen.add(current)
        owner_records = by_owner.get(current, [])
        if not owner_records:
            return DnsAnswer(name, typ, "NXDOMAIN", _ordered(answers), tuple(chain))
        direct = [r for r in owner_records if r.type == typ]
        if direct:
            answers.extend(direct)
            return DnsAnswer(name, typ, "NOERROR", _ordered(answers), tuple(chain))
        if typ != "CNAME":
            cnames = sorted((r for r in owner_records if r.type == "CNAME"), key=lambda r: (r.data, r.ttl))
            if cnames:
                cname = cnames[0]
                answers.append(cname)
                current = cname.data[0]
                continue
        return DnsAnswer(name, typ, "NOERROR", _ordered(answers), tuple(chain))
    chain.append(current)
    return DnsAnswer(name, typ, "CNAME_LOOP", _ordered(answers), tuple(chain))
