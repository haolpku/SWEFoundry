# SWEFoundry family smoke tasks

This batch exercises three deterministic task families without domain-expert
reward labels:

| Task | Family | Starter | Reward oracle |
| --- | --- | --- | --- |
| `repair-jsonl-ledger` | `synthetic-repair` | Deliberately defective module | Hidden behavioral tests |
| `build-feature-flags` | `nl2repo-lite` | Empty package workspace | Install/import and API tests |
| `reproduce-url-router` | `repo-reproduction` | Public API stub plus queryable oracle | Differential-style behavior tests |

All tasks use Harbor's directory conventions: `instruction.md`, `task.toml`,
`environment/`, `solution/`, and `tests/`. They are intentionally small smoke
tasks, not benchmark releases or difficulty-calibrated training data.

Run the independent local audit from the repository root:

```sh
.venv/bin/python scripts/validate_family_smoke.py
```

The audit creates a fresh workspace for every attempt. Each Starter must score
below 1, each Oracle must score exactly 1, and two Oracle repetitions must
produce the same reward payload.
