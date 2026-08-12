#!/usr/bin/env python3
import json
import re
import sys


NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def compile_routes(specs):
    seen = set()
    routes = []
    for index, item in enumerate(specs):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("invalid route")
        route_name, pattern = item
        if not isinstance(route_name, str) or not isinstance(pattern, str) or not pattern.startswith("/"):
            raise ValueError("invalid route")
        if pattern in seen:
            raise ValueError("duplicate pattern")
        seen.add(pattern)
        segments = [] if pattern == "/" else pattern.strip("/").split("/")
        parsed = []
        for position, segment in enumerate(segments):
            if segment.startswith((":", "*")):
                kind, name = segment[0], segment[1:]
                if not NAME.fullmatch(name) or (kind == "*" and position != len(segments) - 1):
                    raise ValueError("invalid pattern")
                parsed.append((kind, name))
            elif not segment:
                raise ValueError("invalid pattern")
            else:
                parsed.append(("s", segment))
        routes.append((route_name, parsed, index))
    return routes


def match(routes, path):
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("invalid path")
    parts = [] if path == "/" else path.strip("/").split("/")
    candidates = []
    for route_name, segments, index in routes:
        captures = {}
        cursor = 0
        ranks = []
        valid = True
        for kind, value in segments:
            if kind == "*":
                captures[value] = "/".join(parts[cursor:])
                cursor = len(parts)
                ranks.append(0)
                break
            if cursor >= len(parts) or not parts[cursor]:
                valid = False
                break
            if kind == "s" and parts[cursor] != value:
                valid = False
                break
            if kind == ":":
                captures[value] = parts[cursor]
            ranks.append(2 if kind == "s" else 1)
            cursor += 1
        if valid and cursor == len(parts):
            candidates.append((tuple(ranks), -index, route_name, captures))
    if not candidates:
        return None
    _, _, route_name, captures = max(candidates)
    return {"name": route_name, "params": captures}


for line in sys.stdin:
    try:
        request = json.loads(line)
        routes = compile_routes(request["specs"])
        result = {"ok": True, "result": True if request["op"] == "compile" else match(routes, request["path"])}
    except Exception as exc:
        result = {"ok": False, "error": type(exc).__name__}
    print(json.dumps(result, sort_keys=True), flush=True)
