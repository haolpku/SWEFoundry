# SWEFoundry coding-family roadmap

## Goal

SWEFoundry will support six requested data directions through one execution
and data control plane:

- long-horizon coding;
- NL2Repo;
- Terminal-Bench;
- SWE-bench;
- DeepSWE;
- FrontierSWE.

Support and generation are separate milestones. Supporting a benchmark means
that its source tasks can be imported without losing identity, materialized,
validated, rolled out, scored, filtered, and exported. Generating new tasks
also requires an independently trustworthy query, workspace, verifier, Oracle
or reference behavior, contamination controls, and calibrated difficulty.

## Common abstraction

`long-horizon` is a task profile rather than a standalone family. A task is
represented on two axes:

| Axis | Values |
| --- | --- |
| Objective | repo generation, repo repair, repo evolution, terminal state transition, performance optimization, research |
| Horizon | short, medium, long, ultra-long |

The common record chain remains:

```text
TaskRecord --1:N--> TrajectoryRecord --1:1 or 1:N--> RewardRecord
```

Each family adapter owns only the semantics that cannot be standardized:

```python
import_records(source, source_ref, dataset_version)
validate_record(record)
package_for_harbor(source, output, source_ref, dataset_version)
```

Future adapters will extend this boundary with materialization, Oracle QA,
scoring, and progress extraction while preserving the record contract.

## Family matrix

| Family | Workspace | Primary reward | Automated generation outlook |
| --- | --- | --- | --- |
| NL2Repo | empty repository or minimal scaffold | build + API + behavioral hidden tests | High, if contract and tests are independently produced |
| Terminal-Bench | container/filesystem state | artifact and end-state verifier | High for deterministic system tasks |
| SWE-bench | pinned repository snapshot | FAIL_TO_PASS + PASS_TO_PASS | High for mutation-based repair; medium for mined real issues |
| DeepSWE | pinned repository, broad change surface | multi-implementation behavioral tests | Medium for implementation/evolution subsets |
| FrontierSWE | large repository and specialized resources | correctness-gated continuous metric | Low without experts; performance subsets are feasible |

## Phase A — unified execution

Target: prove format support before producing new tasks.

1. Import 3–5 source tasks from each available family.
2. Preserve original task ID, dataset version, repository commit, source URI,
   license/provenance, verifier contract, and content hash.
3. Materialize each workspace from a clean cache.
4. Require Oracle/reference success and Starter/baseline non-success where the
   source benchmark exposes both.
5. Run through Harbor and emit ATIF, `TrajectoryRecord`, and `RewardRecord`.
6. Verify deterministic rescoring and export release shards.

Current v0.4 status:

- Terminal-Bench directory import, deterministic recipe compilation, local
  Starter/Oracle QA, and Harbor packaging work;
- SWE-bench JSON/JSONL import, single-fault mutation generation, pinned
  image/commit runtime packaging, and per-test hidden reward compilation work;
- NL2Repo contract import, independent-artifact provenance gates, empty-repo
  Harbor compilation, and local Starter/Oracle QA work;
- DeepSWE and FrontierSWE have registered capability descriptors, without a
  false claim of runnable import or generation support.

Exit gate: at least 15 smoke tasks across the available families execute twice
with stable task hashes and rewards.

## Phase B — scalable task production

Build generators in this order.

### B1. SWE repair

1. Select repositories with reproducible builds and clear licenses.
2. Pin repository, dependency, and container versions.
3. Inject one bounded mutant into code covered by existing tests.
4. Generate an issue-style query from behavior, without exposing the patch.
5. Use the unmutated code as Oracle behavior.
6. Add independently generated hidden tests and additional mutants.
7. Keep only tasks where Starter fails, Oracle passes, and plausible wrong
   implementations are rejected.

Pilot target: 50 tasks. Scale target after calibration: 500–1,000 tasks.

### B2. NL2Repo

Use a contract-first pipeline:

```text
machine-readable contract
  -> natural-language requirements
  -> independent reference implementation
  -> independent behavioral tests
  -> verifier mutation audit
```

Reward components should cover installation/build, public interfaces,
behavior, robustness, and constraint compliance. Query, solution, and tests
must not be generated in a single dependent call.

Pilot target: 20–50 tasks. Scale target: 100–300 tasks.

### B3. Terminal tasks

Prioritize deterministic data transformation, build/configuration, service
setup, filesystem, database migration, debugging, and reproducible scientific
computing tasks. Defer tasks whose result quality requires subjective or
specialist review.

Pilot target: 20–50 tasks. Scale target: 100–300 tasks.

## Phase C — long-horizon composition

Compose already verified primitives instead of asking one model to invent an
unstructured multi-hour task:

```text
setup -> diagnose -> implement -> migrate -> optimize -> regress -> package
```

Add to the task contract:

- named milestones and dependency edges;
- checkpoint artifacts and resumability;
- progress, regression, and final reward components;
- best-checkpoint retention;
- rollback and lost-progress detection;
- wall-time, token, tool-call, network, and compute budgets.

The final verifier remains authoritative. Milestone rewards provide useful
partial trajectories but cannot turn a broken final artifact into a full pass.

Pilot target: 10–20 tasks. Scale target: 30–100 tasks after multi-hour
reproducibility is demonstrated.

## Phase D — DeepSWE-like and FrontierSWE-like tasks

### DeepSWE-like

Start with complex implementation and repository-evolution tasks. Require
multi-implementation verifier audits, broad change-surface statistics, and
tests that accept behaviorally correct alternatives rather than matching one
reference patch.

Pilot target: 10–20 tasks; 20–50 only after verifier audits are stable.

### FrontierSWE-like

Without experts, restrict new tasks to programmatically verifiable subsets:

- correctness gate plus runtime speedup;
- correctness gate plus memory reduction;
- compression ratio;
- hidden workload coverage;
- differential equivalence against a pinned implementation.

Research, post-training, and scientific-discovery tasks remain expert-gated.
The near-term milestone is reliable import, rollout, and continuous scoring of
existing tasks, not a task-count target.

## Rollout and promotion gates

Every generated task passes three independent gates.

### Task correctness

- clean materialization;
- Starter/baseline does not already solve the task;
- Oracle/reference passes repeatedly;
- hidden tests are deterministic;
- mutants and anti-hack probes are rejected;
- license, secrets, network, and resource policies pass.

### Difficulty calibration

- multiple model families;
- multiple seeds or attempts;
- full-pass rate and mean partial reward;
- broken-vs-frontier disambiguation through Oracle and manual failure audit;
- no scaling of trivial, impossible, or unstable tasks.

### Trajectory quality

- valid ATIF and terminal observations;
- no infrastructure exception;
- reward artifacts agree or satisfy strict recovered-rescore rules;
- bounded action repetition and empty observations;
- compile/compliance and anti-cheat gates pass;
- accepted, partial, and rejected trajectories remain distinguishable.

## Release and storage

GitHub contains the framework, schemas, recipes, manifests, tests, and tiny
smoke fixtures. Hugging Face stores released record shards and public task
artifacts. VEPFS/object storage holds raw repositories, Docker layers, hidden
verifiers, restricted solutions, rollout logs, and full trajectories.

The first scale decision is made only after Phase A evidence exists. The unit
of scale is a verified task with several calibrated trajectories, not a raw
LLM-generated prompt.
