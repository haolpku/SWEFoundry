---
pretty_name: SWEFoundry Test
task_categories:
  - text-generation
tags:
  - code
  - software-engineering
  - coding-agent
  - harbor
  - trajectory
size_categories:
  - n<1K
---

# SWEFoundry Test

Public smoke data for validating the SWEFoundry task-production contract across
multiple software-engineering task families.

## Included task families

| Task | Family | Behavioral cases | Starter reward | Oracle reward |
| --- | --- | ---: | ---: | ---: |
| `build-feature-flags` | `nl2repo-lite` | 8 | 0.00 | 1.00 |
| `repair-jsonl-ledger` | `synthetic-repair` | 8 | 0.25 | 1.00 |
| `reproduce-url-router` | `repo-reproduction` | 10 | 0.10 | 1.00 |

Every task includes a natural-language instruction, Harbor `task.toml`, Docker
environment, Starter workspace, reference solution, and executable verifier.
The verifier emits both a scalar `reward.txt` and structured `reward.json`.

`data/tasks.jsonl` provides one index row per task for Dataset Viewer. Complete
task artifacts are stored under `family-smoke-v1/tasks/`.

## Validation

The independent audit requires:

- Starter reward below 1.0;
- two fresh Oracle runs with reward exactly 1.0;
- identical structured rewards across repeated Oracle runs;
- no network access in the committed Harbor task policy.

The three tasks pass 26 behavioral checks in total. The source repository's
test suite passes 36 tests.

## Intended use

Use this dataset to test task ingestion, Harbor execution, verifier behavior,
trajectory rollout, and filtering infrastructure. These tasks are deliberately
small and their reference solutions are public. They must not be treated as a
held-out benchmark or used to make contamination-resistant capability claims.

## Source

[SWEFoundry on GitHub](https://github.com/haolpku/SWEFoundry)
