"""Public immutable record types used by the sync engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IcalEvent:
    uid: str
    dtstart: str
    dtend: str = ""
    summary: str = ""
    rrule: dict[str, str] = field(default_factory=dict)
    exdates: tuple[str, ...] = ()
    sequence: int = 0
    status: str = "CONFIRMED"
    recurrence_id: str = ""
    updated: str = ""
    parameters: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class IcalOccurrence:
    uid: str
    recurrence_id: str
    start: str
    end: str
    summary: str
    sequence: int
    status: str


@dataclass(frozen=True)
class IcalSyncChange:
    action: str
    event: IcalEvent | None = None
    uid: str = ""
    recurrence_id: str = ""
    sequence: int = 0
    updated: str = ""


@dataclass(frozen=True)
class IcalConflictDecision:
    uid: str
    recurrence_id: str
    winner: IcalEvent
    losers: tuple[IcalEvent, ...]
    reason: str


@dataclass(frozen=True)
class IcalSyncAuditReport:
    snapshot_version: int
    events: tuple[IcalEvent, ...]
    occurrences: tuple[IcalOccurrence, ...]
    conflicts: tuple[IcalConflictDecision, ...]
    warnings: tuple[str, ...] = ()
