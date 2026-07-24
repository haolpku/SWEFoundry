"""Starter public API wrappers. The starter is intentionally incomplete."""

from __future__ import annotations

from .core import audit_ical_sync_impl, apply_ical_sync_impl, expand_ical_recurrences_impl, parse_icalendar_impl, resolve_ical_conflicts_impl
from .models import IcalConflictDecision, IcalEvent, IcalOccurrence, IcalSyncAuditReport, IcalSyncChange

FEATURE_LEVEL = 0


def parse_icalendar(text: str) -> list[IcalEvent]:
    return parse_icalendar_impl(text, unfold=FEATURE_LEVEL >= 1)


def expand_ical_recurrences(events: list[IcalEvent], start: str, end: str) -> list[IcalOccurrence]:
    return expand_ical_recurrences_impl(events, start, end, full=FEATURE_LEVEL >= 2)


def apply_ical_sync(base: list[IcalEvent], changes: list[IcalSyncChange]) -> list[IcalEvent]:
    return apply_ical_sync_impl(base, changes, full=FEATURE_LEVEL >= 3)


def resolve_ical_conflicts(candidates: list[IcalEvent]) -> list[IcalConflictDecision]:
    return resolve_ical_conflicts_impl(candidates, full=FEATURE_LEVEL >= 4)


def audit_ical_sync(snapshot: str, incoming: str, window_start: str, window_end: str) -> IcalSyncAuditReport:
    return audit_ical_sync_impl(snapshot, incoming, window_start, window_end, full=FEATURE_LEVEL >= 5)
