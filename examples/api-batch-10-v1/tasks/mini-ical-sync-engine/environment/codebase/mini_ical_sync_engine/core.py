"""Deterministic implementation helpers for the public engine wrappers."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Iterable

from .exceptions import IcalParseError, IcalValidationError
from .models import IcalConflictDecision, IcalEvent, IcalOccurrence, IcalSyncAuditReport, IcalSyncChange


def _event_key(event: IcalEvent) -> tuple[str, str]:
    return (event.uid, event.recurrence_id)


def _sort_events(events: Iterable[IcalEvent]) -> list[IcalEvent]:
    return sorted(events, key=lambda e: (e.uid, e.recurrence_id, e.dtstart, e.sequence, e.updated))


def _unfold(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines: list[str] = []
    for line in raw:
        if line == "":
            continue
        if line[:1] in (" ", "\t"):
            if not lines:
                raise IcalParseError("folded content line has no previous line")
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _not_unfolded(text: str) -> list[str]:
    return [line for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line]


def _parse_params(left: str) -> tuple[str, dict[str, tuple[str, ...]]]:
    parts = left.split(";")
    name = parts[0].upper()
    params: dict[str, tuple[str, ...]] = {}
    for part in parts[1:]:
        if "=" not in part:
            params[part.upper()] = ()
            continue
        key, value = part.split("=", 1)
        params[key.upper()] = tuple(v.strip('"') for v in value.split(","))
    return name, params


def _parse_rrule(value: str) -> dict[str, str]:
    rule: dict[str, str] = {}
    for item in value.split(";"):
        if not item:
            continue
        if "=" not in item:
            raise IcalParseError("RRULE item lacks '='")
        key, val = item.split("=", 1)
        rule[key.upper()] = val.upper()
    return rule


def parse_icalendar_impl(text: str, *, unfold: bool = True) -> list[IcalEvent]:
    lines = _unfold(text) if unfold else _not_unfolded(text)
    in_event = False
    props: dict[str, list[tuple[str, dict[str, tuple[str, ...]]]]] = {}
    events: list[IcalEvent] = []
    for line in lines:
        if ":" not in line:
            raise IcalParseError(f"content line lacks colon: {line}")
        left, value = line.split(":", 1)
        name, params = _parse_params(left)
        if name == "BEGIN" and value.upper() == "VEVENT":
            if in_event:
                raise IcalParseError("nested VEVENT is not supported")
            in_event = True
            props = {}
            continue
        if name == "END" and value.upper() == "VEVENT":
            if not in_event:
                raise IcalParseError("END:VEVENT without BEGIN:VEVENT")
            uid = _one(props, "UID", required=True)
            dtstart = _one(props, "DTSTART", required=True)
            dtend = _one(props, "DTEND", required=False)
            sequence_text = _one(props, "SEQUENCE", required=False) or "0"
            try:
                sequence = int(sequence_text)
            except ValueError as exc:
                raise IcalParseError("SEQUENCE must be an integer") from exc
            rrule_text = _one(props, "RRULE", required=False)
            exdates: list[str] = []
            for value_text, _ in props.get("EXDATE", []):
                exdates.extend(part for part in value_text.split(",") if part)
            all_params: dict[str, tuple[str, ...]] = {}
            for values in props.values():
                for _, param_map in values:
                    for key, vals in param_map.items():
                        all_params[key] = vals
            events.append(IcalEvent(
                uid=uid,
                dtstart=dtstart,
                dtend=dtend,
                summary=_one(props, "SUMMARY", required=False) or "",
                rrule=_parse_rrule(rrule_text) if rrule_text else {},
                exdates=tuple(sorted(_canonical_dt(x) for x in exdates)),
                sequence=sequence,
                status=(_one(props, "STATUS", required=False) or "CONFIRMED").upper(),
                recurrence_id=_one(props, "RECURRENCE-ID", required=False) or "",
                updated=_one(props, "LAST-MODIFIED", required=False) or _one(props, "DTSTAMP", required=False) or "",
                parameters=all_params,
            ))
            in_event = False
            props = {}
            continue
        if in_event:
            props.setdefault(name, []).append((value, params))
    if in_event:
        raise IcalParseError("unterminated VEVENT")
    return _sort_events(events)


def _one(props: dict[str, list[tuple[str, dict[str, tuple[str, ...]]]]], name: str, *, required: bool) -> str:
    values = props.get(name, [])
    if not values:
        if required:
            raise IcalValidationError(f"VEVENT missing required {name}")
        return ""
    return values[-1][0]


def _to_datetime(value: str) -> datetime:
    value = value.strip().upper()
    if value.endswith("Z"):
        value = value[:-1]
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise IcalValidationError(f"unsupported date-time value: {value}")


def _canonical_dt(value: str) -> str:
    return _to_datetime(value).strftime("%Y%m%dT%H%M%S")


def _format_dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _duration(event: IcalEvent) -> timedelta:
    if not event.dtend:
        return timedelta(0)
    delta = _to_datetime(event.dtend) - _to_datetime(event.dtstart)
    if delta < timedelta(0):
        raise IcalValidationError("DTEND must not be before DTSTART")
    return delta


def expand_ical_recurrences_impl(events: list[IcalEvent], start: str, end: str, *, full: bool = True) -> list[IcalOccurrence]:
    window_start = _to_datetime(start)
    window_end = _to_datetime(end)
    if window_end < window_start:
        raise IcalValidationError("window end must not be before start")
    occurrences: list[IcalOccurrence] = []
    for event in _sort_events(events):
        if event.status == "CANCELLED":
            continue
        if not full or not event.rrule:
            candidates = [_to_datetime(event.dtstart)]
        else:
            candidates = _recurrence_starts(event)
        delta = _duration(event)
        exdates = set(event.exdates)
        for occ_start in candidates:
            canon_start = _format_dt(occ_start)
            if canon_start in exdates:
                continue
            if occ_start < window_start or occ_start >= window_end:
                continue
            occurrences.append(IcalOccurrence(
                uid=event.uid,
                recurrence_id=event.recurrence_id or canon_start,
                start=canon_start,
                end=_format_dt(occ_start + delta),
                summary=event.summary,
                sequence=event.sequence,
                status=event.status,
            ))
    return sorted(occurrences, key=lambda o: (o.start, o.uid, o.recurrence_id, o.sequence))


def _recurrence_starts(event: IcalEvent) -> list[datetime]:
    rule = event.rrule
    freq = rule.get("FREQ", "").upper()
    if freq not in {"DAILY", "WEEKLY"}:
        raise IcalValidationError(f"unsupported FREQ: {freq}")
    interval = int(rule.get("INTERVAL", "1"))
    if interval <= 0:
        raise IcalValidationError("RRULE INTERVAL must be positive")
    count = int(rule["COUNT"]) if "COUNT" in rule else None
    until = _to_datetime(rule["UNTIL"]) if "UNTIL" in rule else None
    step = timedelta(days=interval if freq == "DAILY" else 7 * interval)
    current = _to_datetime(event.dtstart)
    starts: list[datetime] = []
    generated = 0
    limit = 10000
    while limit > 0:
        limit -= 1
        if count is not None and generated >= count:
            break
        if until is not None and current > until:
            break
        starts.append(current)
        generated += 1
        current += step
    if limit == 0:
        raise IcalValidationError("recurrence expansion exceeded deterministic safety limit")
    return starts


def _newer(left_sequence: int, left_updated: str, right_sequence: int, right_updated: str) -> bool:
    return (left_sequence, left_updated) >= (right_sequence, right_updated)


def apply_ical_sync_impl(base: list[IcalEvent], changes: list[IcalSyncChange], *, full: bool = True) -> list[IcalEvent]:
    if not full:
        return _sort_events([e for e in base if e.status != "CANCELLED"])
    records: dict[tuple[str, str], IcalEvent] = {_event_key(e): e for e in base}
    tombstones: dict[tuple[str, str], tuple[int, str]] = {}
    for event in base:
        if event.status == "CANCELLED":
            tombstones[_event_key(event)] = (event.sequence, event.updated)
    ordered = sorted(changes, key=lambda c: (c.uid or (c.event.uid if c.event else ""), c.recurrence_id or (c.event.recurrence_id if c.event else ""), c.sequence, c.updated, c.action))
    for change in ordered:
        action = change.action.upper()
        if action in {"CREATE", "UPDATE"}:
            if change.event is None:
                raise IcalValidationError("create/update change requires event")
            key = _event_key(change.event)
            tomb = tombstones.get(key)
            if tomb and not _newer(change.event.sequence, change.event.updated, tomb[0], tomb[1]):
                continue
            current = records.get(key)
            if current is None or _newer(change.event.sequence, change.event.updated, current.sequence, current.updated):
                records[key] = change.event
                if change.event.status == "CANCELLED":
                    tombstones[key] = (change.event.sequence, change.event.updated)
        elif action == "DELETE":
            uid = change.uid or (change.event.uid if change.event else "")
            rid = change.recurrence_id or (change.event.recurrence_id if change.event else "")
            key = (uid, rid)
            current = records.get(key)
            seq = max(change.sequence, current.sequence if current else 0)
            updated = change.updated or (current.updated if current else "")
            if current is None or _newer(seq, updated, current.sequence, current.updated):
                tomb = IcalEvent(uid=uid, recurrence_id=rid, dtstart=current.dtstart if current else "19700101T000000", dtend=current.dtend if current else "19700101T000000", summary=current.summary if current else "", sequence=seq, updated=updated, status="CANCELLED")
                records[key] = tomb
                tombstones[key] = (seq, updated)
        else:
            raise IcalValidationError(f"unsupported sync action: {change.action}")
    return _sort_events([event for event in records.values() if event.status != "CANCELLED"])


def resolve_ical_conflicts_impl(candidates: list[IcalEvent], *, full: bool = True) -> list[IcalConflictDecision]:
    groups: dict[tuple[str, str], list[IcalEvent]] = {}
    for event in candidates:
        groups.setdefault(_event_key(event), []).append(event)
    decisions: list[IcalConflictDecision] = []
    for key in sorted(groups):
        group = groups[key]
        if full:
            winner = max(group, key=lambda e: (e.sequence, e.updated, 1 if e.status == "CANCELLED" else 0, e.uid, e.recurrence_id, e.dtstart, e.summary))
        else:
            winner = group[0]
        losers = tuple(sorted((e for e in group if e is not winner), key=lambda e: (e.sequence, e.updated, e.status, e.dtstart, e.summary)))
        if losers:
            reason = f"winner selected by sequence={winner.sequence}, updated={winner.updated or '<empty>'}, status={winner.status}, uid={winner.uid}, recurrence_id={winner.recurrence_id or '<master>'}"
            decisions.append(IcalConflictDecision(uid=key[0], recurrence_id=key[1], winner=winner, losers=losers, reason=reason))
    return decisions


def _event_to_dict(event: IcalEvent) -> dict[str, object]:
    data = asdict(event)
    data["exdates"] = list(event.exdates)
    return data


def _event_from_dict(data: dict[str, object]) -> IcalEvent:
    return IcalEvent(
        uid=str(data.get("uid", "")),
        dtstart=str(data.get("dtstart", "")),
        dtend=str(data.get("dtend", "")),
        summary=str(data.get("summary", "")),
        rrule={str(k).upper(): str(v).upper() for k, v in dict(data.get("rrule", {})).items()},
        exdates=tuple(sorted(_canonical_dt(str(x)) for x in data.get("exdates", []))),
        sequence=int(data.get("sequence", 0)),
        status=str(data.get("status", "CONFIRMED")).upper(),
        recurrence_id=str(data.get("recurrence_id", "")),
        updated=str(data.get("updated", "")),
        parameters={str(k): tuple(str(vv) for vv in v) for k, v in dict(data.get("parameters", {})).items()},
    )


def _load_snapshot(snapshot: str) -> tuple[int, list[IcalEvent], list[str]]:
    warnings: list[str] = []
    text = snapshot.strip()
    if not text:
        return 2, [], ()
    if text.startswith("{"):
        data = json.loads(text)
        version = int(data.get("version", 1))
        if version != 2:
            warnings.append(f"migrated snapshot version {version} to 2")
        events = [_event_from_dict(item) for item in data.get("events", [])]
        return 2, _sort_events(events), warnings
    warnings.append("migrated text snapshot to version 2")
    return 2, parse_icalendar_impl(snapshot), warnings


def audit_ical_sync_impl(snapshot: str, incoming: str, window_start: str, window_end: str, *, full: bool = True) -> IcalSyncAuditReport:
    if not full:
        raise IcalValidationError("integrated audit is not available until step 5")
    version, snapshot_events, warnings = _load_snapshot(snapshot)
    incoming_events = parse_icalendar_impl(incoming) if incoming.strip() else []
    decisions = resolve_ical_conflicts_impl(snapshot_events + incoming_events, full=True)
    winner_keys = {_event_key(decision.winner): decision.winner for decision in decisions}
    untouched = {_event_key(event): event for event in snapshot_events + incoming_events if _event_key(event) not in winner_keys}
    merged = list(untouched.values()) + list(winner_keys.values())
    final_events = _sort_events([event for event in merged if event.status != "CANCELLED"])
    occurrences = expand_ical_recurrences_impl(final_events, window_start, window_end, full=True)
    return IcalSyncAuditReport(snapshot_version=version, events=tuple(final_events), occurrences=tuple(occurrences), conflicts=tuple(decisions), warnings=tuple(warnings))


def write_snapshot_atomic(path: str, events: list[IcalEvent]) -> None:
    payload = json.dumps({"version": 2, "events": [_event_to_dict(e) for e in _sort_events(events)]}, sort_keys=True, separators=(",", ":"))
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".ical-sync-", suffix=".tmp", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
