#!/usr/bin/env python3
import sys
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_ical_sync_engine import IcalEvent, IcalSyncChange, apply_ical_sync


def main():
    base = [IcalEvent(uid='u', dtstart='20250101T090000', dtend='20250101T100000', summary='old', sequence=1)]
    newer = IcalEvent(uid='u', dtstart='20250101T090000', dtend='20250101T100000', summary='new', sequence=2)
    result = apply_ical_sync(base, [IcalSyncChange(action='UPDATE', event=newer)])
    assert [(e.uid, e.summary, e.sequence) for e in result] == [('u','new',2)]
    deleted = apply_ical_sync(result, [IcalSyncChange(action='DELETE', uid='u', sequence=3)])
    assert deleted == []


if __name__ == '__main__':
    main()
