"""Step 5 public API: complete deterministic Oracle is enabled."""

from __future__ import annotations

from .core import audit_ical_sync_impl, apply_ical_sync_impl, expand_ical_recurrences_impl, parse_icalendar_impl, resolve_ical_conflicts_impl
from .models import IcalConflictDecision, IcalEvent, IcalOccurrence, IcalSyncAuditReport, IcalSyncChange

FEATURE_LEVEL = 5


def parse_icalendar(text: str) -> list[IcalEvent]:
    return parse_icalendar_impl(text, unfold=True)


def expand_ical_recurrences(events: list[IcalEvent], start: str, end: str) -> list[IcalOccurrence]:
    return expand_ical_recurrences_impl(events, start, end, full=True)


def apply_ical_sync(base: list[IcalEvent], changes: list[IcalSyncChange]) -> list[IcalEvent]:
    return apply_ical_sync_impl(base, changes, full=True)


def resolve_ical_conflicts(candidates: list[IcalEvent]) -> list[IcalConflictDecision]:
    return resolve_ical_conflicts_impl(candidates, full=True)


def audit_ical_sync(snapshot: str, incoming: str, window_start: str, window_end: str) -> IcalSyncAuditReport:
    return audit_ical_sync_impl(snapshot, incoming, window_start, window_end, full=True)
