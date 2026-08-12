from __future__ import annotations

from pathlib import Path

from .base import read_json_rows
from .production import compile_harbor_task, spec_from_recipe


def generate_terminal_tasks(recipes: Path, output: Path) -> list[Path]:
    tasks = []
    for row in read_json_rows(recipes):
        tasks.append(compile_harbor_task(spec_from_recipe(row, expected_family="terminal-bench"), output))
    return tasks
