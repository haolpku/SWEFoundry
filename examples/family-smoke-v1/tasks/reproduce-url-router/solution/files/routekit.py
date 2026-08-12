from __future__ import annotations

import re


_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def compile_routes(specs):
    if not isinstance(specs, list):
        raise ValueError("specs must be a list")
    seen = set()
    routes = []
    for index, item in enumerate(specs):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("invalid route")
        route_name, pattern = item
        if not isinstance(route_name, str) or not route_name or not isinstance(pattern, str) or not pattern.startswith("/"):
            raise ValueError("invalid route")
        if pattern != "/" and pattern.endswith("/"):
            raise ValueError("invalid pattern")
        if pattern in seen:
            raise ValueError("duplicate pattern")
        seen.add(pattern)
        raw_segments = [] if pattern == "/" else pattern[1:].split("/")
        segments = []
        for position, segment in enumerate(raw_segments):
            if not segment:
                raise ValueError("empty pattern segment")
            if segment.startswith((":", "*")):
                kind, name = segment[0], segment[1:]
                if not _NAME.fullmatch(name) or (kind == "*" and position != len(raw_segments) - 1):
                    raise ValueError("invalid capture")
                segments.append((kind, name))
            else:
                segments.append(("static", segment))
        routes.append((route_name, tuple(segments), index))
    return tuple(routes)


def match(compiled, path):
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("path must begin with slash")
    parts = [] if path == "/" else path.strip("/").split("/")
    candidates = []
    for route_name, segments, declaration_index in compiled:
        captures = {}
        cursor = 0
        specificity = []
        matched = True
        for kind, value in segments:
            if kind == "*":
                captures[value] = "/".join(parts[cursor:])
                cursor = len(parts)
                specificity.append(0)
                break
            if cursor >= len(parts) or not parts[cursor]:
                matched = False
                break
            if kind == "static":
                if parts[cursor] != value:
                    matched = False
                    break
                specificity.append(2)
            else:
                captures[value] = parts[cursor]
                specificity.append(1)
            cursor += 1
        if matched and cursor == len(parts):
            candidates.append((tuple(specificity), -declaration_index, route_name, captures))
    if not candidates:
        return None
    _, _, route_name, captures = max(candidates)
    return {"name": route_name, "params": captures}
