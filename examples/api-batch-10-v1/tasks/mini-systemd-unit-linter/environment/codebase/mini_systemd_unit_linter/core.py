from __future__ import annotations

from dataclasses import dataclass
import os

from .exceptions import DependencyCycleError
from . import policy

_DEP_KEYS = ('Requires', 'Wants', 'After', 'Before', 'Conflicts')


def _norm(name: str) -> str:
    return os.path.basename(str(name).strip()).lower()


def _strip_comment(line: str) -> str:
    for index, char in enumerate(line):
        if char in '#;':
            return line[:index]
    return line


def _split_words(value: str) -> tuple[str, ...]:
    return tuple(_norm(part) for part in value.split() if part.strip())


@dataclass(frozen=True)
class UnitFile:
    name: str
    path: str
    sections: dict[str, dict[str, str]]

    def get(self, section: str, key: str, default: str = '') -> str:
        return self.sections.get(section, {}).get(key, default)

    def values(self, key: str) -> tuple[str, ...]:
        found: list[str] = []
        for section in ('Unit', 'Install', 'Service'):
            value = self.sections.get(section, {}).get(key, '')
            if value:
                found.extend(_split_words(value))
        return tuple(found)


@dataclass(frozen=True, order=True)
class UnitProblem:
    severity: str
    unit: str
    kind: str
    dependency: str
    message: str


@dataclass(frozen=True)
class BootReplay:
    started: tuple[str, ...]
    skipped: tuple[str, ...]
    failed: tuple[str, ...]


@dataclass(frozen=True)
class UnitAuditReport:
    units: tuple[str, ...]
    problems: tuple[UnitProblem, ...]
    plan: tuple[str, ...]
    replay: BootReplay | None
    errors: tuple[str, ...]
    recovery: tuple[str, ...]


def _parse_file(path: str) -> UnitFile:
    name = _norm(path)
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    with open(path, 'r', encoding='utf-8') as handle:
        for number, raw in enumerate(handle, 1):
            line = _strip_comment(raw).strip()
            if not line:
                continue
            if line.startswith('['):
                if not line.endswith(']') or line.count('[') != 1 or line.count(']') != 1:
                    raise ValueError(f'{path}:{number}: malformed section header')
                current = line[1:-1].strip()
                if not current:
                    raise ValueError(f'{path}:{number}: malformed section header')
                sections.setdefault(current, {})
                continue
            if current is None or '=' not in line:
                raise ValueError(f'{path}:{number}: malformed assignment')
            key, value = line.split('=', 1)
            key = key.strip()
            if not key:
                raise ValueError(f'{path}:{number}: malformed assignment')
            if policy.STRICT_DUPLICATES and key in sections[current]:
                raise ValueError(f'{path}:{number}: duplicate key {current}.{key}')
            sections[current][key] = value.strip()
    return UnitFile(name=name, path=os.path.abspath(path), sections=sections)


def load_units(paths: list[str]) -> list[UnitFile]:
    files: list[str] = []
    for root in sorted(os.path.abspath(path) for path in paths):
        if os.path.isfile(root):
            files.append(root)
            continue
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            full = os.path.join(root, entry)
            if os.path.isfile(full):
                files.append(full)
    units: list[UnitFile] = []
    seen: set[str] = set()
    for path in files:
        unit = _parse_file(path)
        if unit.name in seen:
            raise ValueError(f'duplicate unit name {unit.name}')
        seen.add(unit.name)
        units.append(unit)
    return sorted(units, key=lambda unit: unit.name)


def _unit_map(units: list[UnitFile]) -> dict[str, UnitFile]:
    return {unit.name: unit for unit in sorted(units, key=lambda item: item.name)}


def validate_unit_graph(units: list[UnitFile]) -> list[UnitProblem]:
    known = _unit_map(units)
    problems: list[UnitProblem] = []
    for unit in sorted(units, key=lambda item: item.name):
        for key in _DEP_KEYS:
            for dep in unit.values(key):
                if dep in known:
                    continue
                if key == 'Requires':
                    severity = 'error' if policy.REQUIRES_IS_ERROR else 'warning'
                elif key == 'Conflicts':
                    severity = 'error'
                else:
                    severity = 'warning'
                problems.append(UnitProblem(severity, unit.name, key, dep, f'{unit.name} {key} missing unit {dep}'))
    order = {'error': 0, 'warning': 1, 'info': 2}
    return sorted(problems, key=lambda p: (order.get(p.severity, 9), p.unit, p.kind, p.dependency, p.message))


def _closure(units: dict[str, UnitFile], target: str) -> set[str]:
    target = _norm(target)
    if target not in units:
        raise KeyError(target)
    needed: set[str] = set()
    stack = [target]
    while stack:
        name = stack.pop()
        if name in needed or name not in units:
            continue
        needed.add(name)
        for key in ('Requires', 'Wants'):
            for dep in sorted(units[name].values(key), reverse=True):
                if dep in units and dep not in needed:
                    stack.append(dep)
    return needed


def plan_activation(units: list[UnitFile], target: str) -> list[str]:
    known = _unit_map(units)
    nodes = _closure(known, target)
    for name in sorted(nodes):
        for other in known[name].values('Conflicts'):
            if other in nodes:
                raise ValueError(f'conflict: {name} {other}')
    edges: dict[str, set[str]] = {name: set() for name in nodes}
    indegree: dict[str, int] = {name: 0 for name in nodes}

    def add(before: str, after: str) -> None:
        if before in nodes and after in nodes and after not in edges[before]:
            edges[before].add(after)
            indegree[after] += 1

    for name in sorted(nodes):
        unit = known[name]
        for dep in unit.values('Requires') + unit.values('Wants'):
            add(dep, name)
        for dep in unit.values('After'):
            add(dep, name)
        if policy.HONOR_BEFORE:
            for dep in unit.values('Before'):
                add(name, dep)
    ready = sorted(name for name, degree in indegree.items() if degree == 0)
    result: list[str] = []
    while ready:
        name = ready.pop(0)
        result.append(name)
        for nxt in sorted(edges[name]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort()
    if len(result) != len(nodes):
        raise DependencyCycleError(sorted(set(nodes) - set(result)))
    return result


def _restart_allows_recovery(unit: UnitFile) -> bool:
    mode = unit.get('Service', 'Restart', 'no').strip().lower()
    burst_text = unit.get('Service', 'StartLimitBurst', unit.get('Unit', 'StartLimitBurst', '1')).strip()
    try:
        burst = int(burst_text)
    except ValueError:
        burst = 1
    return mode in {'always', 'on-failure'} and burst > 1


def replay_activation(units: list[UnitFile], plan: list[str], failed: set[str]) -> BootReplay:
    known = _unit_map(units)
    configured_failed = {_norm(name) for name in failed}
    started: set[str] = set()
    skipped: set[str] = set()
    failed_out: set[str] = set()
    for name in [_norm(item) for item in plan]:
        unit = known.get(name)
        if unit is None:
            skipped.add(name)
            continue
        required_bad = [dep for dep in unit.values('Requires') if dep in failed_out or dep in skipped]
        wanted_bad = [dep for dep in unit.values('Wants') if dep in failed_out or dep in skipped]
        if required_bad or (policy.WANTS_FAILURE_FATAL and wanted_bad):
            skipped.add(name)
            continue
        if name in configured_failed and not _restart_allows_recovery(unit):
            failed_out.add(name)
            continue
        started.add(name)
    return BootReplay(tuple(sorted(started)), tuple(sorted(skipped)), tuple(sorted(failed_out)))


def audit_units(paths: list[str], target: str, failed: set[str]) -> UnitAuditReport:
    errors: list[str] = []
    replay: BootReplay | None = None
    plan: list[str] = []
    try:
        units = load_units(paths)
    except Exception as exc:
        return UnitAuditReport((), (), (), None, (f'load: {exc}',), ())
    problems = tuple(validate_unit_graph(units))
    try:
        plan = plan_activation(units, target)
        replay = replay_activation(units, plan, failed)
    except DependencyCycleError as exc:
        errors.append(str(exc))
        if not policy.KEEP_VALIDATION_ON_CYCLE:
            problems = ()
    except Exception as exc:
        errors.append(str(exc))
    recovery: tuple[str, ...]
    if replay is None:
        recovery = ()
    else:
        recovery = tuple(sorted([f'started:{name}' for name in replay.started] + [f'skipped:{name}' for name in replay.skipped] + [f'failed:{name}' for name in replay.failed]))
    return UnitAuditReport(tuple(unit.name for unit in units), problems, tuple(plan), replay, tuple(errors), recovery)
