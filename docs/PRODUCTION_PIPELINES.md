# P0 production pipelines

SWEFoundry v0.4 closes the executable packaging gap for deterministic
Terminal-Bench-like, mutation-based SWE-bench-like, and contract-first
NL2Repo tasks. It does not automatically certify model-generated semantics.
Promotion still requires independent QA and rollout calibration.

## Terminal-Bench-like

Input: JSON or JSONL rows conforming to `schemas/terminal-recipe.schema.json`.
Each recipe contains the visible instruction, starter files, Oracle files, and
hidden verifier files.

```sh
swef terminal-generate \
  --recipes /data/recipes/terminal.jsonl \
  --output /data/candidates/terminal

swef production-qa \
  --tasks-root /data/candidates/terminal \
  --output /data/qa/terminal.json
```

The compiler rejects absolute/traversing artifact paths and existing output
directories. The local QA gate requires Starter reward below 1, repeated
Oracle reward equal to 1, and byte-stable structured rewards.

## Mutation-based SWE repair

Input: a clean checkout at the declared `base_commit` plus mutation recipes
conforming to `schemas/swe-mutation-recipe.schema.json`.

```sh
swef swe-mutate \
  --repo /vepfs/repos/project \
  --recipes /data/recipes/swe.jsonl \
  --output /data/instances/swe-mutated.jsonl

swef family-package \
  --family swe-bench \
  --source /data/instances/swe-mutated.jsonl \
  --source-ref local://swe-mutated-v1 \
  --dataset-version v1 \
  --output /data/candidates/swe
```

`swe-mutate` requires exactly one source match and emits both the injected bug
patch and its inverse gold patch. The packager supports a pinned SWE image
(`image_name` plus `repo_path`) or a pinned GitHub URL/commit fallback. It
creates a no-network Harbor task and executes each declared test separately
without `shell=True`.

SWE workspaces are materialized by an image or clone, so they are intentionally
rejected by local `production-qa`. Run Harbor Oracle and Nop/Starter jobs,
preferably twice, and attach their evidence before promotion. A source-built
fallback also needs dependency installation encoded in its base image; an
official/prefetched SWE image is the production path.

## Contract-first NL2Repo

Input bundles conform to `schemas/nl2repo-production.schema.json` and contain:

- a machine-readable contract and visible instruction;
- starter files;
- independently generated reference files;
- independently generated hidden verifier files;
- distinct contract, solution, and verifier generation run IDs.

```sh
swef family-package \
  --family nl2repo \
  --source /data/bundles/nl2repo.jsonl \
  --source-ref local://nl2repo-v1 \
  --dataset-version v1 \
  --output /data/candidates/nl2repo

swef production-qa \
  --tasks-root /data/candidates/nl2repo \
  --output /data/qa/nl2repo.json
```

Distinct run IDs are a machine-enforced provenance gate, not proof of true
independence. The production orchestrator must use different generation calls
and should use different model families for reference implementation and
hidden tests when feasible.

## Promotion gate

A compiled directory is a candidate, not accepted data. Promotion requires:

1. schema and family validation;
2. Starter/Nop non-pass;
3. repeated Oracle full pass and deterministic reward;
4. mutant and anti-hack rejection;
5. Harbor execution with stable artifact collection;
6. task hash, source lineage, license, and secret scan;
7. multi-model rollout difficulty calibration;
8. accepted trajectory filtering and HF shard export.

Production artifacts belong on VEPFS/Hugging Face, not in Git.
