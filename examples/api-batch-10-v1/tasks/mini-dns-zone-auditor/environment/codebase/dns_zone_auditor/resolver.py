"""Starter deterministic offline resolver."""
from __future__ import annotations

from .models import DnsAnswer, DnsRecord


def _canon(name: str) -> str:
    return name.lower() if name.endswith(".") else name.lower() + "."


def answer_zone(records: list[DnsRecord], qname: str, qtype: str) -> DnsAnswer:
    name = _canon(qname)
    typ = qtype.upper()
    answers = tuple(r for r in records if r.owner == name and r.type == typ)
    rcode = "NOERROR" if answers else "NXDOMAIN"
    return DnsAnswer(name, typ, rcode, answers, (name,))
