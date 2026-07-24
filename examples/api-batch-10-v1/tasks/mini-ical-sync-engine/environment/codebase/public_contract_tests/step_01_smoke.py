#!/usr/bin/env python3
import sys
from pathlib import Path

CODEBASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_ical_sync_engine import parse_icalendar


def main():
    text = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:folded-public','DTSTART:20250101T090000','DTEND:20250101T100000','SUMMARY:Hello',' world','SEQUENCE:1','STATUS:CONFIRMED','END:VEVENT','END:VCALENDAR',''])
    events = parse_icalendar(text)
    assert [e.uid for e in events] == ['folded-public']
    assert events[0].summary == 'Helloworld'
    bad = chr(10).join(['BEGIN:VCALENDAR','BEGIN:VEVENT','DTSTART:20250101T090000','END:VEVENT','END:VCALENDAR',''])
    try:
        parse_icalendar(bad)
    except Exception:
        pass
    else:
        raise AssertionError('missing UID must raise')


if __name__ == '__main__':
    main()
