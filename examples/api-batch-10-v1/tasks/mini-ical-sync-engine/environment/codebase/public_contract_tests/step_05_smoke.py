#!/usr/bin/env python3
import json
import sys
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_ical_sync_engine import audit_ical_sync


def main():
    snapshot = json.dumps({'version':1,'events':[{'uid':'s','dtstart':'20250101T090000','dtend':'20250101T100000','summary':'snapshot','sequence':1}]})
    incoming = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:s','DTSTART:20250101T090000','DTEND:20250101T100000','SUMMARY:incoming','SEQUENCE:2','END:VEVENT','END:VCALENDAR',''])
    report = audit_ical_sync(snapshot, incoming, '20250101T000000', '20250102T000000')
    assert report.snapshot_version == 2
    assert [e.summary for e in report.events] == ['incoming']
    assert [o.summary for o in report.occurrences] == ['incoming']
    assert report.conflicts and 'migrated snapshot version 1 to 2' in report.warnings


if __name__ == '__main__':
    main()
