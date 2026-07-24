#!/usr/bin/env python3
"""Normalize mechanical verifier packaging drift without changing test semantics."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path, PurePosixPath

from terminal_data_factory.operators.core import atomic_json


STEP = re.compile(r"^steps/([1-5])-[^/]+/")


def normalized_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.as_posix() == "environment/codebase/public_contract_tests/README":
        return "environment/codebase/public_contract_tests/README.md"
    parts = path.parts
    if path.suffix == ".py" and re.fullmatch(r"fp[1-5][^/]*\.py", path.name):
        if parts[0] == "mutants":
            return (PurePosixPath("verifier/anti_cheat") / path.name).as_posix()
        if parts[:2] == ("verifier", "mutants"):
            return (PurePosixPath("verifier/anti_cheat") / path.name).as_posix()
        if len(parts) == 2 and parts[0] == "verifier":
            return (PurePosixPath("verifier/anti_cheat") / path.name).as_posix()
    return path.as_posix()


def _flatten_path_join(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _flatten_path_join(node.left) + [node.right]
    return [node]


def _path_join(parts: list[ast.AST]) -> ast.AST:
    result = parts[0]
    for part in parts[1:]:
        result = ast.BinOp(left=result, op=ast.Div(), right=part)
    return result


class _AuditMutantPathNormalizer(ast.NodeTransformer):
    """Rewrite only filesystem joins/list entries that target moved mutants."""

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        node = self.generic_visit(node)
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            return node
        parts = _flatten_path_join(node)
        values = [
            part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else None
            for part in parts
        ]
        strings = [value for value in values if value is not None]
        if "mutants" in strings:
            rewritten: list[ast.AST] = []
            for index, (part, value) in enumerate(zip(parts, values)):
                if value == "mutants":
                    if index > 0 and values[index - 1] == "verifier":
                        rewritten.append(ast.Constant("anti_cheat"))
                    else:
                        rewritten.extend(
                            [ast.Constant("verifier"), ast.Constant("anti_cheat")]
                        )
                else:
                    rewritten.append(part)
            return ast.copy_location(_path_join(rewritten), node)
        if "verifier" in strings and any(
            isinstance(value, str) and re.fullmatch(r"fp[1-5][^/]*\.py", value)
            for value in strings
        ) and "anti_cheat" not in strings:
            index = values.index("verifier") + 1
            parts.insert(index, ast.Constant("anti_cheat"))
            return ast.copy_location(_path_join(parts), node)
        if (
            "verifier" in strings
            and "anti_cheat" not in strings
            and isinstance(parts[-1], ast.Name)
            and parts[-1].id in {"mutant", "mutant_name"}
        ):
            index = values.index("verifier") + 1
            parts.insert(index, ast.Constant("anti_cheat"))
            return ast.copy_location(_path_join(parts), node)
        return node

    def visit_List(self, node: ast.List) -> ast.AST:
        node = self.generic_visit(node)
        values = [
            item.value if isinstance(item, ast.Constant) else None
            for item in node.elts
        ]
        if "verifier" in values and "mutants" in values:
            node.elts = [
                item
                for item in node.elts
                if not (isinstance(item, ast.Constant) and item.value == "mutants")
            ]
        return node

    def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
        node = self.generic_visit(node)
        values = [
            item.value if isinstance(item, ast.Constant) else None
            for item in node.elts
        ]
        if "verifier" in values and "mutants" in values:
            node.elts = [
                item
                for item in node.elts
                if not (isinstance(item, ast.Constant) and item.value == "mutants")
            ]
        return node

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        node = self.generic_visit(node)
        for index, key in enumerate(node.keys):
            if (
                isinstance(key, ast.Constant)
                and key.value in {"all_passed", "overall_pass", "ok"}
            ):
                node.keys[index] = ast.copy_location(ast.Constant("passed"), key)
        return node

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        node = self.generic_visit(node)
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in {"all_passed", "overall_pass", "ok"}
        ):
            node.slice = ast.copy_location(ast.Constant("passed"), node.slice)
        return node


def normalize_run_audit(source: str) -> str:
    tree = ast.parse(source, filename="verifier/run_audit.py")
    normalized = _AuditMutantPathNormalizer().visit(tree)
    ast.fix_missing_locations(normalized)
    rendered = ast.unparse(normalized)
    if source.startswith("#!"):
        rendered = source.splitlines()[0] + "\n" + rendered
    return rendered.rstrip() + "\n"


def normalize_payload(payload: dict) -> tuple[dict, list[dict[str, str]], list[str]]:
    if payload.get("schema_version") != "1.0" or payload.get("fragment") != "verification":
        raise ValueError("input must be a schema 1.0 verification fragment")
    files = payload.get("files")
    if not isinstance(files, list):
        raise ValueError("verification files must be a list")
    mapping = {item["path"]: normalized_path(item["path"]) for item in files}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("normalization would create duplicate paths")
    replacements = sorted(
        ((old, new) for old, new in mapping.items() if old != new),
        key=lambda item: -len(item[0]),
    )
    moved_mutants = any(
        new.startswith("verifier/anti_cheat/") and old != new
        for old, new in replacements
    )
    content_changes: list[str] = []
    for item in files:
        item["path"] = mapping[item["path"]]
        content = item["content"]
        for old, new in replacements:
            content = content.replace(old, new)
        match = STEP.match(item["path"])
        if match and item["path"].endswith("/instruction.md"):
            number = int(match.group(1))
            smoke = f"python public_contract_tests/step_{number:02d}_smoke.py"
            if "/app/knowledge/public_api.md" not in content or smoke not in content:
                content = (
                    content.rstrip()
                    + "\n\n## Public contract self-check\n\n"
                    + "Read `/app/knowledge/public_api.md` before implementation. "
                    + f"From `/app/workspace`, run `{smoke}`.\n"
                )
                content_changes.append(f"instruction-contract:{item['path']}")
        if match and item["path"].endswith("/tests/test.sh"):
            if (
                "env -u PYTHONPATH -u PYTHONHOME" not in content
                or " -I " not in content
            ):
                lines = content.splitlines()
                changed = False
                for index in range(len(lines) - 1, -1, -1):
                    line = lines[index]
                    if (
                        not changed
                        and "verifier.py" in line
                        and not line.lstrip().startswith("#")
                    ):
                        indent = line[: len(line) - len(line.lstrip())]
                        invocation = line.strip()
                        exec_prefix = ""
                        if invocation.startswith("exec "):
                            exec_prefix = "exec "
                            invocation = invocation.removeprefix("exec ")
                        elif re.search(r"(^|\s)exec\s+", invocation):
                            # Environment assignments commonly precede ``exec``.
                            # Shell requires exec to wrap the final env command,
                            # not to appear as env's executable name.
                            invocation = re.sub(
                                r"(^|\s)exec\s+",
                                lambda match: match.group(1),
                                invocation,
                                count=1,
                            )
                            exec_prefix = "exec "
                        if "env -u PYTHONPATH -u PYTHONHOME" not in invocation:
                            invocation = (
                                "env -u PYTHONPATH -u PYTHONHOME " + invocation
                            )
                        invocation, count = re.subn(
                            r"\b(python(?:3(?:\.\d+)?)?)\s+(?!-I(?:\s|$))",
                            r"\1 -I ",
                            invocation,
                            count=1,
                        )
                        if count != 1 and not re.search(
                            r"\bpython(?:3(?:\.\d+)?)?\s+-I(?:\s|$)",
                            invocation,
                        ):
                            raise ValueError(
                                f"cannot identify Python invocation in {item['path']}"
                            )
                        lines[index] = indent + exec_prefix + invocation
                        changed = True
                if not changed:
                    raise ValueError(
                        f"cannot identify verifier invocation in {item['path']}"
                    )
                content = "\n".join(lines) + "\n"
                content_changes.append(f"test-isolation:{item['path']}")
        if item["path"] == "verifier/run_audit.py":
            normalized_audit = normalize_run_audit(content)
            if normalized_audit != content:
                content = normalized_audit
                label = (
                    "audit-mutant-paths-and-schema:verifier/run_audit.py"
                    if moved_mutants
                    else "audit-schema:verifier/run_audit.py"
                )
                content_changes.append(label)
        item["content"] = content
    changed_paths = [
        {"from": old, "to": new}
        for old, new in mapping.items()
        if old != new
    ]
    return payload, changed_paths, content_changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    try:
        payload, changed_paths, content_changes = normalize_payload(payload)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    output = Path(args.output or args.input)
    atomic_json(output, payload)
    print(
        json.dumps(
            {
                "task_id": payload.get("task_id"),
                "changed_paths": changed_paths,
                "content_changes": content_changes,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
