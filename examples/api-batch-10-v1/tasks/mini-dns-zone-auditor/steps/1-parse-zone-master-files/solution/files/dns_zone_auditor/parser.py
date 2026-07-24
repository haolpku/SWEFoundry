"""Parser for a restricted deterministic RFC 1035 master-file subset."""
from __future__ import annotations

import ipaddress
from typing import List

from .exceptions import ZoneParseError
from .models import DnsRecord

_SUPPORTED = {"SOA", "NS", "A", "AAAA", "CNAME", "TXT"}


def _strip_comment(line: str) -> str:
    out: list[str] = []
    quoted = False
    escaped = False
    for ch in line:
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == "\\" and quoted:
            escaped = True
        elif ch == '"':
            quoted = not quoted
            out.append(ch)
        elif ch == ";" and not quoted:
            break
        else:
            out.append(ch)
    if quoted:
        raise ZoneParseError("unterminated quoted string")
    return "".join(out).strip()


def _logical_lines(text: str) -> list[str]:
    lines: list[str] = []
    buf: list[str] = []
    depth = 0
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line:
            continue
        depth += line.count("(") - line.count(")")
        buf.append(line.replace("(", " ").replace(")", " "))
        if depth < 0:
            raise ZoneParseError("unbalanced parentheses")
        if depth == 0:
            lines.append(" ".join(buf))
            buf = []
    if depth != 0:
        raise ZoneParseError("unbalanced parentheses")
    return lines


def _tokens(line: str) -> list[str]:
    tokens: list[str] = []
    cur: list[str] = []
    quoted = False
    escaped = False
    for ch in line:
        if escaped:
            cur.append(ch)
            escaped = False
        elif ch == "\\" and quoted:
            escaped = True
        elif ch == '"':
            quoted = not quoted
        elif ch.isspace() and not quoted:
            if cur:
                tokens.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if quoted:
        raise ZoneParseError("unterminated quoted string")
    if cur:
        tokens.append("".join(cur))
    return tokens


def _canonical_origin(origin: str) -> str:
    origin = origin.strip()
    if not origin:
        raise ZoneParseError("origin is required")
    return (origin if origin.endswith(".") else origin + ".").lower()


def _name(name: str, origin: str) -> str:
    if not name:
        raise ZoneParseError("empty domain name")
    if name == "@":
        return origin
    if name.endswith("."):
        return name.lower()
    return (name + "." + origin).lower()


def _int(value: str, label: str) -> int:
    try:
        result = int(value, 10)
    except ValueError as exc:
        raise ZoneParseError(f"invalid {label}: {value}") from exc
    if result < 0:
        raise ZoneParseError(f"invalid {label}: {value}")
    return result


def parse_zone(text: str, origin: str) -> list[DnsRecord]:
    current_origin = _canonical_origin(origin)
    default_ttl = 3600
    last_owner: str | None = None
    records: List[DnsRecord] = []
    for line in _logical_lines(text):
        parts = _tokens(line)
        if not parts:
            continue
        directive = parts[0].upper()
        if directive == "$ORIGIN":
            if len(parts) != 2:
                raise ZoneParseError("$ORIGIN requires exactly one argument")
            current_origin = _canonical_origin(parts[1])
            continue
        if directive == "$TTL":
            if len(parts) != 2:
                raise ZoneParseError("$TTL requires exactly one argument")
            default_ttl = _int(parts[1], "ttl")
            continue
        idx = 0
        if parts[idx].upper() == "IN" or parts[idx].isdigit():
            if last_owner is None:
                raise ZoneParseError("record without owner")
            owner = last_owner
        else:
            owner = _name(parts[idx], current_origin)
            last_owner = owner
            idx += 1
        ttl = default_ttl
        if idx < len(parts) and parts[idx].isdigit():
            ttl = _int(parts[idx], "ttl")
            idx += 1
        if idx < len(parts) and parts[idx].upper() == "IN":
            idx += 1
        if idx >= len(parts):
            raise ZoneParseError("missing rr type")
        rtype = parts[idx].upper()
        idx += 1
        rest = parts[idx:]
        if rtype not in _SUPPORTED:
            raise ZoneParseError(f"unsupported rr type: {rtype}")
        if rtype == "SOA":
            if len(rest) != 7:
                raise ZoneParseError("SOA requires seven fields")
            data = (_name(rest[0], current_origin), _name(rest[1], current_origin)) + tuple(str(_int(x, "soa number")) for x in rest[2:])
        elif rtype in {"NS", "CNAME"}:
            if len(rest) != 1:
                raise ZoneParseError(f"{rtype} requires one target")
            data = (_name(rest[0], current_origin),)
        elif rtype == "A":
            if len(rest) != 1:
                raise ZoneParseError("A requires one address")
            ipaddress.IPv4Address(rest[0])
            data = (rest[0],)
        elif rtype == "AAAA":
            if len(rest) != 1:
                raise ZoneParseError("AAAA requires one address")
            data = (str(ipaddress.IPv6Address(rest[0])),)
        else:
            if not rest:
                raise ZoneParseError("TXT requires text")
            data = (" ".join(rest),)
        records.append(DnsRecord(owner, rtype, ttl, data))
    return sorted(records, key=lambda r: (r.owner, r.type, r.data, r.ttl))
