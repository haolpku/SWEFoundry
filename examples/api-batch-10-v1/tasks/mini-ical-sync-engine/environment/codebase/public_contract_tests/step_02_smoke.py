#!/usr/bin/env python3
import sys
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_ical_sync_engine import IcalEvent, expand_ical_recurrences


def main():
    event = IcalEvent(uid='daily-public', dtstart='20250101T090000', dtend='20250101T100000', summary='Daily', rrule={'FREQ':'DAILY','COUNT':'3'})
    occ = expand_ical_recurrences([event], '20250101T000000', '20250105T000000')
    assert [o.start for o in occ] == ['20250101T090000','20250102T090000','20250103T090000']
    event2 = IcalEvent(uid='ex-public', dtstart='20250101T090000', dtend='20250101T100000', rrule={'FREQ':'DAILY','COUNT':'3'}, exdates=('20250102T090000',))
    occ2 = expand_ical_recurrences([event2], '20250101T000000', '20250105T000000')
    assert [o.start for o in occ2] == ['20250101T090000','20250103T090000']


if __name__ == '__main__':
    main()
