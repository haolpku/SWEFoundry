"""Shared deterministic models and helpers for the HTTP cache benchmark."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import email.utils
import json
import os
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlsplit

from .exceptions import CachePolicyError, UnsafeMethodError

_SAFE_PATH = "/-._~!$&'()*+,;=:@"
_SAFE_QUERY = "-._~!$'()*+,;=:@/?"
_HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}
_BODY_HEADERS = {"content-length", "content-range", "content-type", "content-encoding", "content-language", "content-location", "digest"}
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class HttpCacheEntry:
    key: str
    method: str
    scheme: str
    host: str
    path: str
    query: str
    vary: tuple[str, ...] = ()
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    status: int = 200
    body: str = ""
    stored_at: int = 0

    @property
    def effective_uri(self) -> str:
        q = ("?" + self.query) if self.query else ""
        return f"{self.scheme}://{self.host}{self.path}{q}"

    def to_snapshot_record(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "method": self.method,
            "scheme": self.scheme,
            "host": self.host,
            "path": self.path,
            "query": self.query,
            "vary": list(self.vary),
            "request_headers": dict(sorted(self.request_headers.items())),
            "response_headers": dict(sorted(self.response_headers.items())),
            "status": self.status,
            "body": self.body,
            "stored_at": self.stored_at,
        }


@dataclass(frozen=True)
class FreshnessDecision:
    status: str
    age: int
    freshness_lifetime: int
    expires_at: int
    can_use_stale_if_error: bool
    reason: str
    validators: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvalidationResult:
    affected_keys: list[str]
    retained_entries: list[HttpCacheEntry]
    reason: str


@dataclass(frozen=True)
class HttpCacheAuditReport:
    recovered_entries: list[HttpCacheEntry]
    fresh_keys: list[str]
    stale_keys: list[str]
    unusable_keys: list[str]
    invalidated_keys: list[str]
    recovery_actions: list[str]
    decisions: dict[str, FreshnessDecision]


def lower_headers(mapping: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    nested = mapping.get("headers") if isinstance(mapping.get("headers"), dict) else None
    if nested:
        for k, v in nested.items():
            out[str(k).strip().lower()] = " ".join(str(v).strip().split())
    known = {"method", "scheme", "host", "path", "query", "url", "status", "body", "stored_at", "headers"}
    for k, v in mapping.items():
        lk = str(k).strip().lower()
        if lk.startswith("header:"):
            out[lk.split(":", 1)[1].strip().lower()] = " ".join(str(v).strip().split())
        elif lk not in known and v is not None:
            out[lk] = " ".join(str(v).strip().split())
    return dict(sorted(out.items()))


def get_ci(mapping: dict[str, Any], name: str, default: str = "") -> str:
    lname = name.lower()
    for k, v in mapping.items():
        if str(k).lower() == lname:
            return str(v)
    headers = mapping.get("headers")
    if isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == lname:
                return str(v)
    prefixed = "header:" + lname
    for k, v in mapping.items():
        if str(k).lower() == prefixed:
            return str(v)
    return default


def parse_cache_control(value: str) -> dict[str, str | None]:
    parsed: dict[str, str | None] = {}
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        if "=" in token:
            k, v = token.split("=", 1)
            parsed[k.strip().lower()] = v.strip().strip('"')
        else:
            parsed[token.lower()] = None
    return parsed


def parse_http_date(value: str) -> int | None:
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if dt is None:
        return None
    return int(dt.timestamp())


def parse_int(value: str, default: int = 0) -> int:
    try:
        return max(0, int(str(value).strip()))
    except (TypeError, ValueError):
        return default


def normalize_request(request: dict[str, Any]) -> tuple[str, str, str, str, str, dict[str, str]]:
    url = str(request.get("url", ""))
    split = urlsplit(url) if url else None
    method = str(request.get("method", "GET")).upper().strip()
    scheme = str(request.get("scheme", split.scheme if split else "http") or "http").lower()
    host = str(request.get("host", split.netloc if split else "") or get_ci(request, "host", "")).lower()
    if not host:
        raise CachePolicyError("request host is required")
    path = str(request.get("path", split.path if split else "/") or "/")
    path = quote(unquote(path), safe=_SAFE_PATH)
    raw_query = str(request.get("query", split.query if split else "") or "")
    pairs = parse_qsl(raw_query, keep_blank_values=True, strict_parsing=False)
    query = "&".join(f"{quote(k, safe=_SAFE_QUERY)}={quote(v, safe=_SAFE_QUERY)}" for k, v in sorted(pairs))
    return method, scheme, host, path, query, lower_headers(request)


def vary_names(response: dict[str, Any]) -> tuple[str, ...]:
    raw = get_ci(response, "vary", "")
    if not raw:
        return ()
    names = []
    seen = set()
    for item in raw.split(","):
        name = item.strip().lower()
        if not name:
            continue
        if name == "*":
            raise CachePolicyError("Vary: * is not reusable by this offline cache")
        if name not in seen:
            names.append(name)
            seen.add(name)
    return tuple(names)


def canonical_key(request: dict[str, Any], response: dict[str, Any], include_vary: bool = True) -> str:
    method, scheme, host, path, query, req_headers = normalize_request(request)
    if method not in {"GET", "HEAD"}:
        raise UnsafeMethodError(f"method {method} is not cacheable")
    cc = parse_cache_control(get_ci(response, "cache-control", ""))
    if "no-store" in cc:
        raise CachePolicyError("no-store responses are not retained")
    vary = vary_names(response) if include_vary else ()
    parts = ["v1", method, scheme, host, path, query]
    for name in vary:
        parts.append(f"vary:{name}={req_headers.get(name, '')}")
    return "|".join(parts)


def entry_from_request_response(request: dict[str, Any], response: dict[str, Any], include_vary: bool = True, stored_at: int = 0) -> HttpCacheEntry:
    method, scheme, host, path, query, req_headers = normalize_request(request)
    key = canonical_key(request, response, include_vary=include_vary)
    status = parse_int(str(response.get("status", "200")), 200)
    return HttpCacheEntry(
        key=key,
        method=method,
        scheme=scheme,
        host=host,
        path=path,
        query=query,
        vary=vary_names(response) if include_vary else (),
        request_headers=req_headers,
        response_headers=lower_headers(response),
        status=status,
        body=str(response.get("body", "")),
        stored_at=stored_at,
    )


def evaluate_entry(entry: HttpCacheEntry, now: int, max_age_precedence: bool = True) -> FreshnessDecision:
    headers = entry.response_headers
    cc = parse_cache_control(headers.get("cache-control", ""))
    validators = tuple(v for v in (headers.get("etag", ""), headers.get("last-modified", "")) if v)
    if "no-store" in cc or entry.status not in {200, 203, 204, 206, 300, 301, 404, 410}:
        return FreshnessDecision("unusable", 0, 0, now, False, "not retainable", validators)
    date_value = parse_http_date(headers.get("date", ""))
    apparent_age = max(0, now - date_value) if date_value is not None else max(0, now - entry.stored_at)
    age = max(parse_int(headers.get("age", "0")), apparent_age)
    expires_value = parse_http_date(headers.get("expires", ""))
    lifetime = 0
    reason = "no explicit lifetime"
    if max_age_precedence and "max-age" in cc:
        lifetime = parse_int(str(cc.get("max-age") or "0"))
        reason = "cache-control max-age"
    elif expires_value is not None and date_value is not None:
        lifetime = max(0, expires_value - date_value)
        reason = "expires"
    elif not max_age_precedence and "max-age" in cc:
        lifetime = parse_int(str(cc.get("max-age") or "0"))
        reason = "cache-control max-age"
    expires_at = now + max(0, lifetime - age)
    stale_if_error = parse_int(str(cc.get("stale-if-error") or "0"))
    if age < lifetime:
        return FreshnessDecision("fresh", age, lifetime, expires_at, False, reason, validators)
    if stale_if_error and age < lifetime + stale_if_error:
        return FreshnessDecision("stale", age, lifetime, expires_at, True, "stale-if-error", validators)
    return FreshnessDecision("stale", age, lifetime, expires_at, False, "expired", validators)


def merge_304(entry: HttpCacheEntry, response_304: dict[str, Any], preserve_body: bool = True) -> HttpCacheEntry:
    incoming = lower_headers(response_304)
    cached_etag = entry.response_headers.get("etag", "")
    new_etag = incoming.get("etag", "")
    if cached_etag and new_etag and cached_etag != new_etag:
        raise ValueError("304 ETag does not match cached entry")
    cached_lm = entry.response_headers.get("last-modified", "")
    new_lm = incoming.get("last-modified", "")
    if cached_lm and new_lm and cached_lm != new_lm:
        raise ValueError("304 Last-Modified does not match cached entry")
    merged = dict(entry.response_headers)
    for k, v in incoming.items():
        if k in _HOP_BY_HOP or k in {"content-length", "content-range"}:
            continue
        merged[k] = v
    if cached_etag and "etag" not in merged:
        merged["etag"] = cached_etag
    body = entry.body if preserve_body else str(response_304.get("body", ""))
    return replace(entry, response_headers=dict(sorted(merged.items())), body=body)


def event_uri(event: dict[str, Any]) -> str:
    method, scheme, host, path, query, _ = normalize_request({
        "method": event.get("method", "GET"),
        "scheme": event.get("scheme", "http"),
        "host": event.get("host", ""),
        "path": event.get("path", "/"),
        "query": event.get("query", ""),
        "url": event.get("url", ""),
    })
    del method
    return f"{scheme}://{host}{path}" + (("?" + query) if query else "")


def invalidate_entries(entries: list[HttpCacheEntry], event: dict[str, Any], all_variants: bool = True) -> InvalidationResult:
    etype = str(event.get("type", "method")).lower()
    method = str(event.get("method", "GET")).upper()
    affected: set[str] = set()
    reason = "no-op"
    if etype == "purge" and event.get("key"):
        target = str(event["key"])
        affected = {e.key for e in entries if e.key == target}
        reason = "explicit purge key"
    elif etype == "purge" or method in _UNSAFE_METHODS:
        uri = event_uri(event)
        if all_variants:
            affected = {e.key for e in entries if e.effective_uri == uri}
            reason = "uri variants invalidated"
        else:
            target = str(event.get("key", ""))
            affected = {e.key for e in entries if e.key == target}
            reason = "exact key invalidated"
    if etype == "no-store":
        affected |= {e.key for e in entries if "no-store" in parse_cache_control(e.response_headers.get("cache-control", ""))}
        reason = "no-store not retained"
    retained = [e for e in entries if e.key not in affected and "no-store" not in parse_cache_control(e.response_headers.get("cache-control", ""))]
    return InvalidationResult(sorted(affected), sorted(retained, key=lambda e: e.key), reason)


def entry_from_snapshot(record: dict[str, Any]) -> HttpCacheEntry:
    request = {
        "method": record.get("method", "GET"),
        "scheme": record.get("scheme", "http"),
        "host": record.get("host", ""),
        "path": record.get("path", "/"),
        "query": record.get("query", ""),
        "headers": record.get("request_headers", {}),
    }
    response = {"headers": record.get("response_headers", {}), "status": str(record.get("status", 200)), "body": record.get("body", "")}
    key = canonical_key(request, response, include_vary=True)
    if record.get("key") and str(record.get("key")) != key:
        raise CachePolicyError("snapshot key does not match canonical metadata")
    return HttpCacheEntry(
        key=key,
        method=request["method"],
        scheme=str(request["scheme"]).lower(),
        host=str(request["host"]).lower(),
        path=quote(unquote(str(request["path"] or "/")), safe=_SAFE_PATH),
        query=normalize_request(request)[4],
        vary=tuple(str(x).lower() for x in record.get("vary", vary_names(response))),
        request_headers=lower_headers({"headers": record.get("request_headers", {})}),
        response_headers=lower_headers({"headers": record.get("response_headers", {})}),
        status=parse_int(str(record.get("status", 200)), 200),
        body=str(record.get("body", "")),
        stored_at=parse_int(str(record.get("stored_at", 0)), 0),
    )


def load_snapshot(path: str) -> tuple[list[HttpCacheEntry], list[str]]:
    actions: list[str] = []
    if not path or not os.path.exists(path):
        return [], ["snapshot-missing"]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return [], ["snapshot-unreadable"]
    records = raw.get("entries", raw) if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        return [], ["snapshot-has-no-entry-list"]
    entries: list[HttpCacheEntry] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            actions.append(f"record-{index}-ignored-not-object")
            continue
        try:
            entry = entry_from_snapshot(record)
        except (CachePolicyError, UnsafeMethodError, TypeError, ValueError) as exc:
            actions.append(f"record-{index}-ignored-{exc.__class__.__name__}")
            continue
        if entry.key in seen:
            actions.append(f"record-{index}-ignored-duplicate-key")
            continue
        seen.add(entry.key)
        entries.append(entry)
    if not actions:
        actions.append("snapshot-valid")
    return sorted(entries, key=lambda e: e.key), actions


def audit_snapshot(path: str, events: list[dict[str, Any]], now: int, validate_first: bool = True) -> HttpCacheAuditReport:
    if validate_first:
        entries, actions = load_snapshot(path)
    else:
        entries, actions = [], ["events-applied-before-validation"]
        for ev in events:
            try:
                invalidate_entries(entries, ev, all_variants=False)
            except Exception:
                actions.append("prevalidation-event-failed")
        valid, valid_actions = load_snapshot(path)
        entries.extend(valid)
        actions.extend(valid_actions)
    invalidated: set[str] = set()
    for event in events:
        result = invalidate_entries(entries, event, all_variants=True)
        invalidated.update(result.affected_keys)
        entries = result.retained_entries
    decisions: dict[str, FreshnessDecision] = {}
    fresh: list[str] = []
    stale: list[str] = []
    unusable: list[str] = []
    for entry in sorted(entries, key=lambda e: e.key):
        decision = evaluate_entry(entry, now, max_age_precedence=True)
        decisions[entry.key] = decision
        if decision.status == "fresh":
            fresh.append(entry.key)
        elif decision.status == "stale":
            stale.append(entry.key)
        else:
            unusable.append(entry.key)
    return HttpCacheAuditReport(sorted(entries, key=lambda e: e.key), fresh, stale, unusable, sorted(invalidated), actions, decisions)
