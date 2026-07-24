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
        records: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
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
    for item in items:
        if not isinstance(item, dict):
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
    if not isinstance(value, str) or value == "":
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
    covers: tuple[str, ...] = ()
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
    seen: dict[str, NotebookOp] = {}
    for record in _load_records(text):
        op = _make_op(record)
        seen[op.op_id] = op
    return sorted(seen.values(), key=lambda op: (op.actor, op.seq))


def validate_notebook_dag(ops: list[NotebookOp]) -> list[CrdtProblem]:
    return []


def merge_notebook_text(ops: list[NotebookOp]) -> list[NotebookCell]:
    return []


def plan_notebook_compaction(ops: list[NotebookOp], peer_frontiers: dict[str, list[str]]) -> CrdtCompactionPlan:
    return CrdtCompactionPlan()


def audit_crdt_notebook(snapshot: str | None, journal: str, peer_frontiers: dict[str, list[str]]) -> CrdtNotebookAuditReport:
    ops = tuple(parse_notebook_ops(journal))
    return CrdtNotebookAuditReport(operations=ops)
