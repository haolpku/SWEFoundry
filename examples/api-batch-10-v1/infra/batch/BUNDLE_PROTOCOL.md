# Model fragment and batch materialization protocol

Each task is synthesized into three independent JSON fragments:

- `core`
- `verification`
- `package`

The package fragment is deterministic and must be compiled after the model
workers finish `core` and `verification`:

```bash
PYTHONPATH=src .venv-harbor/bin/python scripts/compile_package_fragment.py \
  --blueprint accepted/mini-example.blueprint.json \
  --contract accepted/mini-example.contract.json \
  --core-fragment fragments/mini-example/core.json \
  --verification-fragment fragments/mini-example/verification.json \
  --output fragments/mini-example/package.json
```

The compiler derives the task ID, five canonical Step names, public contract,
source and license from accepted inputs. It parses literal verifier `CASES`
with Python's AST and records only statically confirmed named cases. It emits
Harbor schema 1.3 metadata with `under-construction`, zero target rollouts and
uncalibrated difficulty; it never promotes static completeness into a
difficulty claim.

Every fragment declares `schema_version: "1.0"`, a lowercase kebab-case
`task_id`, its `fragment` name, and a `files` array. Workers may run in
parallel. The merger rejects task-id mixing, duplicate fragment names,
duplicate file paths, absolute paths, and traversal paths.

Merge one task:

```bash
PYTHONPATH=src .venv-harbor/bin/python scripts/merge_model_fragments.py \
  --task-id mini-example \
  --fragment fragments/mini-example/core.json \
  --fragment fragments/mini-example/verification.json \
  --fragment fragments/mini-example/package.json \
  --output bundles/mini-example.json
```

Before writing any source file, the materializer requires:

- exactly five numbered step roots;
- `instruction.md`, `solution/solve.sh`, `tests/verifier.py`, and
  `tests/test.sh` for every step;
- exactly five Python mutants whose filenames cover Steps 1 through 5;
- the task metadata, Dockerfile, knowledge and public API files;
- a top-level audit runner;
- no secret-like string, IP/private endpoint, host user path, path traversal,
  duplicate path, or non-boolean executable flag.

Publish a ten-task batch transactionally:

```bash
PYTHONPATH=src .venv-harbor/bin/python scripts/materialize_model_batch.py \
  --expected-count 10 \
  --bundle bundles/mini-a.json \
  --bundle bundles/mini-b.json \
  ... \
  --output materialized-tasks
```

All ten bundles are validated before the output directory is created. Task IDs
must be unique. Materialization happens in a sibling staging directory and is
renamed into place only when all files have been written. A
`BATCH_MANIFEST.json` records sorted task IDs and per-task file counts.

The materializer does not assert semantic correctness. Oracle/Starter,
mutant-rejection, isolation, repeatability, Harbor and target-agent rollout
operators remain mandatory downstream gates.
