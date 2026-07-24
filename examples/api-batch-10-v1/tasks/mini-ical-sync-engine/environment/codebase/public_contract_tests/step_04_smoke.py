#!/usr/bin/env python3
import sys
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_ical_sync_engine import IcalEvent, resolve_ical_conflicts


def main():
    old = IcalEvent(uid='c', dtstart='20250101T090000', dtend='20250101T100000', summary='old', sequence=1, updated='20250101T000000')
    new = IcalEvent(uid='c', dtstart='20250101T090000', dtend='20250101T100000', summary='new', sequence=2, updated='20250102T000000')
    decisions = resolve_ical_conflicts([old, new])
    assert len(decisions) == 1
    assert decisions[0].winner.summary == 'new'
    live = IcalEvent(uid='d', dtstart='20250101T090000', sequence=5, updated='20250101T000000')
    tomb = IcalEvent(uid='d', dtstart='20250101T090000', sequence=5, updated='20250102T000000', status='CANCELLED')
    assert resolve_ical_conflicts([live, tomb])[0].winner.status == 'CANCELLED'


if __name__ == '__main__':
    main()
