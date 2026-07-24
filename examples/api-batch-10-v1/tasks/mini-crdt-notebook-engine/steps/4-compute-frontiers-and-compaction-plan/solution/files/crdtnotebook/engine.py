from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .exceptions import NotebookParseError, NotebookValidationError


@dataclass(frozen=True, order=True)
class NotebookOp:
    actor: str
    seq: int
    op_type: str
    deps: tuple[str, ...] = ()
    cell: str | None = None
    char: str | None = None
    after: str | None = None
    target: str | None = None
    title: str | None = None
    covers: tuple[str, ...] = ()
    raw: tuple[tuple[str, str], ...] = ()

    @property
    def op_id(self) -> str:
        return f"{self.actor}:{self.seq}"


@dataclass(frozen=True, order=True)
class CrdtProblem:
    code: str
    op_id: str
    message: str
    witness: tuple[str, ...] = ()


@dataclass(frozen=True, order=True)
class NotebookCell:
    cell_id: str
    text: str
    title: str = ""
    tombstones: tuple[str, ...] = ()


@dataclass(frozen=True)
class CrdtCompactionPlan:
    peer_frontiers: tuple[tuple[str, tuple[str, ...]], ...] = ()
    stable_tombstones: tuple[str, ...] = ()
    checkpoint_candidates: tuple[str, ...] = ()
    retained_operations: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class CrdtNotebookAuditReport:
    schema_version: str = "1.0"
    operations: tuple[NotebookOp, ...] = ()
    problems: tuple[CrdtProblem, ...] = ()
    cells: tuple[NotebookCell, ...] = ()
    compaction_plan: CrdtCompactionPlan = field(default_factory=CrdtCompactionPlan)
    recovered_from_snapshot: bool = False
    migrated_snapshot: bool = False


def _load_records(text: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        records = []
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped:
                try:
                    item = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise NotebookParseError(f"line {line_no}: {exc.msg}") from exc
                if not isinstance(item, dict):
                    raise NotebookParseError(f"line {line_no}: operation must be an object")
                records.append(item)
        return records
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict):
        items = value.get("operations", value.get("ops", value.get("journal", [])))
    else:
        raise NotebookParseError("top-level JSON must be an array or object")
    if not isinstance(items, list):
        raise NotebookParseError("operation collection must be a list")
    if not all(isinstance(item, dict) for item in items):
        raise NotebookParseError("each operation must be an object")
    return list(items)


def _id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or ":" not in value or value.startswith(":") or value.endswith(":"):
        raise NotebookValidationError(f"{field_name} must be an actor:seq identifier")
    actor, seq = value.rsplit(":", 1)
    if not actor or not seq.isdecimal() or int(seq) < 1:
        raise NotebookValidationError(f"{field_name} must be an actor:seq identifier")
    return value


def _ids(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise NotebookValidationError(f"{field_name} must be a list")
    return tuple(sorted(_id(item, field_name) for item in value))


def _str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise NotebookValidationError(f"{field_name} must be a non-empty string")
    return value


def _make_op(record: dict[str, Any]) -> NotebookOp:
    actor = _str(record.get("actor"), "actor")
    seq = record.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        raise NotebookValidationError("seq must be a positive integer")
    op_type = record.get("type", record.get("op_type", record.get("kind")))
    if op_type not in {"insert", "delete", "set-title", "checkpoint"}:
        raise NotebookValidationError("type must be insert, delete, set-title, or checkpoint")
    deps = _ids(record.get("deps", []), "deps")
    cell = char = after = target = title = None
    covers = ()
    if op_type == "insert":
        cell = _str(record.get("cell", record.get("obj")), "cell")
        ch = record.get("char")
        if not isinstance(ch, str) or len(ch) != 1:
            raise NotebookValidationError("char must be exactly one Unicode character")
        char = ch
        raw_after = record.get("after")
        after = None if raw_after is None else _id(raw_after, "after")
    elif op_type == "delete":
        target = _id(record.get("target", record.get("object")), "target")
        raw_cell = record.get("cell")
        cell = raw_cell if isinstance(raw_cell, str) and raw_cell else None
    elif op_type == "set-title":
        title = _str(record.get("title"), "title")
        raw_cell = record.get("cell")
        cell = raw_cell if isinstance(raw_cell, str) and raw_cell else None
    else:
        covers = _ids(record.get("covers", []), "covers")
    raw = tuple(sorted((str(k), json.dumps(v, sort_keys=True, separators=(",", ":"))) for k, v in record.items()))
    return NotebookOp(actor, seq, op_type, deps, cell, char, after, target, title, covers, raw)


def parse_notebook_ops(text: str) -> list[NotebookOp]:
    seen: set[str] = set()
    ops: list[NotebookOp] = []
    for record in _load_records(text):
        op = _make_op(record)
        if op.op_id in seen:
            raise NotebookValidationError(f"duplicate operation id {op.op_id}")
        seen.add(op.op_id)
        ops.append(op)
    return sorted(ops, key=lambda op: (op.actor, op.seq))


def _canon_cycle(cycle: list[str]) -> tuple[str, ...]:
    if cycle and cycle[0] == cycle[-1]:
        cycle = cycle[:-1]
    variants = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
    return min(variants) if variants else ()


def validate_notebook_dag(ops: list[NotebookOp]) -> list[CrdtProblem]:
    by_id = {op.op_id: op for op in ops}
    problems: list[CrdtProblem] = []
    for actor in sorted({op.actor for op in ops}):
        seqs = sorted(op.seq for op in ops if op.actor == actor)
        for expected, actual in enumerate(seqs, 1):
            if expected != actual:
                problems.append(CrdtProblem("sequence_gap", f"{actor}:{actual}", "actor sequence is not continuous", (f"{actor}:{expected}", f"{actor}:{actual}")))
                break
    graph: dict[str, tuple[str, ...]] = {}
    for op in sorted(ops, key=lambda item: item.op_id):
        refs = list(op.deps)
        if op.op_type == "checkpoint":
            refs.extend(op.covers)
        for ref in refs:
            if ref not in by_id:
                code = "checkpoint_missing" if op.op_type == "checkpoint" and ref in op.covers else "missing_dependency"
                problems.append(CrdtProblem(code, op.op_id, f"referenced operation {ref} is absent", (op.op_id, ref)))
        graph[op.op_id] = tuple(sorted(dep for dep in op.deps if dep in by_id))
    state: dict[str, str] = {}
    stack: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        state[node] = "visiting"
        stack.append(node)
        for dep in graph.get(node, ()):
            if state.get(dep) == "visiting":
                cycles.add(_canon_cycle(stack[stack.index(dep):] + [dep]))
            elif state.get(dep) is None:
                visit(dep)
        stack.pop()
        state[node] = "done"

    for node in sorted(graph):
        if state.get(node) is None:
            visit(node)
    for cycle in sorted(cycles):
        problems.append(CrdtProblem("causal_cycle", cycle[0], "dependency cycle detected", cycle))
    return sorted(problems)


def merge_notebook_text(ops: list[NotebookOp]) -> list[NotebookCell]:
    problems = validate_notebook_dag(ops)
    if problems:
        raise NotebookValidationError("cannot merge invalid causal DAG")
    by_id = {op.op_id: op for op in ops}
    children: dict[str | None, list[str]] = {None: []}
    tombstones: set[str] = set()
    titles: dict[str, str] = {}
    cells: set[str] = set()
    for op in sorted(ops, key=lambda item: (item.actor, item.seq)):
        if op.op_type == "insert":
            cells.add(op.cell or "")
            children.setdefault(op.after, []).append(op.op_id)
            children.setdefault(op.op_id, [])
        elif op.op_type == "delete" and op.target:
            tombstones.add(op.target)
        elif op.op_type == "set-title":
            titles[op.cell or ""] = op.title or ""
    for key in list(children):
        children[key].sort()
    visible: dict[str, list[str]] = {cell: [] for cell in cells}
    dead: dict[str, list[str]] = {cell: [] for cell in cells}

    def walk(parent: str | None) -> None:
        for child in children.get(parent, []):
            op = by_id[child]
            cell_id = op.cell or ""
            if child in tombstones:
                dead.setdefault(cell_id, []).append(child)
            else:
                visible.setdefault(cell_id, []).append(op.char or "")
            walk(child)

    walk(None)
    return [NotebookCell(cell, "".join(visible.get(cell, [])), titles.get(cell, ""), tuple(sorted(dead.get(cell, [])))) for cell in sorted(set(visible) | set(dead) | set(titles))]


def _closure(ops: list[NotebookOp], frontier: list[str]) -> set[str]:
    by_id = {op.op_id: op for op in ops}
    seen: set[str] = set()
    stack = sorted(frontier)
    while stack:
        op_id = stack.pop()
        if op_id in seen or op_id not in by_id:
            continue
        seen.add(op_id)
        stack.extend(by_id[op_id].deps)
    return seen


def plan_notebook_compaction(ops: list[NotebookOp], peer_frontiers: dict[str, list[str]]) -> CrdtCompactionPlan:
    closures = {peer: _closure(ops, ids) for peer, ids in sorted(peer_frontiers.items())}
    if not closures:
        closures = {"local": {op.op_id for op in ops}}
    all_seen = set.intersection(*closures.values()) if closures else set()
    deleted = {op.target: op.op_id for op in ops if op.op_type == "delete" and op.target}
    stable = tuple(sorted(target for target, delete_id in deleted.items() if target in all_seen and delete_id in all_seen))
    checkpoints = tuple(sorted(op.op_id for op in ops if op.op_type == "checkpoint" and set(op.covers).issubset(all_seen)))
    remove = set(stable)
    retained = tuple(sorted(op.op_id for op in ops if op.op_id not in remove))
    actions = tuple(f"compact tombstone {op_id}" for op_id in stable)
    frontiers = tuple((peer, tuple(sorted(ids))) for peer, ids in sorted(peer_frontiers.items()))
    return CrdtCompactionPlan(frontiers, stable, checkpoints, retained, actions)


def audit_crdt_notebook(snapshot: str | None, journal: str, peer_frontiers: dict[str, list[str]]) -> CrdtNotebookAuditReport:
    ops = tuple(parse_notebook_ops(journal))
    return CrdtNotebookAuditReport(operations=ops, problems=tuple(validate_notebook_dag(list(ops))))
