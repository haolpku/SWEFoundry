#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target = workspace / 'environment' / 'codebase' / 'mqtt_session_broker' / 'audit.py'
    text = target.read_text(encoding='utf-8')
    old = '    state = replay_mqtt_events(events)\n'
    new = '    state = replay_mqtt_events(events)\n    if snapshot not in (None, ""):\n        from types import MappingProxyType\n        from .models import BrokerState\n        state = BrokerState(events=state.events, sessions=state.sessions, retained=MappingProxyType({}), retained_tombstones=state.retained_tombstones, deliveries=state.deliveries, expired_clients=state.expired_clients)\n'
    if old not in text:
        raise SystemExit('oracle audit recovery pattern not found')
    target.write_text(text.replace(old, new, 1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
