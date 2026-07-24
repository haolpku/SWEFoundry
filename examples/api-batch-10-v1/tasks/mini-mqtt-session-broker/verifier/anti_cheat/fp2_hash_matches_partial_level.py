#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target = workspace / 'environment' / 'codebase' / 'mqtt_session_broker' / 'matching.py'
    text = target.read_text(encoding='utf-8')
    old_validation = '        if "#" in level and level != "#":\n            raise MqttValidationError("multi-level wildcard must occupy a whole level")\n'
    old_match = '        if level != "+" and level != topic_levels[topic_index]:\n            return False\n        topic_index += 1\n'
    new_match = '        if "#" in level:\n            return topic_levels[topic_index].startswith(level.replace("#", ""))\n        if level != "+" and level != topic_levels[topic_index]:\n            return False\n        topic_index += 1\n'
    if old_validation not in text or old_match not in text:
        raise SystemExit('oracle matching wildcard patterns not found')
    text = text.replace(old_validation, '', 1)
    text = text.replace(old_match, new_match, 1)
    target.write_text(text, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
