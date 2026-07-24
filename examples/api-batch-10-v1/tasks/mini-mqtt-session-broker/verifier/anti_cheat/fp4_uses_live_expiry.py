#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target = workspace / 'environment' / 'codebase' / 'mqtt_session_broker' / 'migration.py'
    text = target.read_text(encoding='utf-8')
    old_import = 'from .models import BrokerState, MqttMigrationAdvice\n'
    new_import = 'import time\n\nfrom .models import BrokerState, MqttMigrationAdvice\n'
    old_return = '    return [MqttMigrationAdvice(category, target, detail, seq) for category, target, detail, seq in sorted(advice)]\n'
    injected = '    if time.monotonic() >= 0:\n        for client_id, session in state.sessions.items():\n            if not session.connected and not session.expired:\n                advice.add(("stale-session", client_id, "session appears expired by elapsed wall clock", 0))\n    return [MqttMigrationAdvice(category, target, detail, seq) for category, target, detail, seq in sorted(advice)]\n'
    if old_import not in text or old_return not in text:
        raise SystemExit('oracle migration patterns not found')
    text = text.replace(old_import, new_import, 1)
    text = text.replace(old_return, injected, 1)
    target.write_text(text, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
