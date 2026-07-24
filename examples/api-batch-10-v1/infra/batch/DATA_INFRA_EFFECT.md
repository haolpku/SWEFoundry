# Data Infra Effect Report

## Experiment

The frozen buyer handoff was left untouched. A separate operator run selected a
ten-topic portfolio, compiled five-Step contracts and mutant plans, then launched
two API worker stages with four-way concurrency:

| Worker stage | Model | Tasks | Success | Recorded tokens |
|---|---|---:|---:|---:|
| final topic portfolio | GPT-5.5 | 10 topics | 1/1 response | 24,178 |
| core/solution synthesis | GPT-5.5 | 10 | 10/10 | 114,215 |
| verifier/anti-cheat synthesis | GPT-5.5 | 10 | 10/10 | 336,594 |
| **Recorded total** |  |  |  | **474,987** |

Credentials were supplied only through process environment variables. Retained
worker metadata uses a redacted endpoint and `credentials_persisted=false`.

## What the operators caught

The value of the infra was not merely producing files. Deterministic gates
rejected or repaired several plausible-looking model outputs before handoff:

- verifier declaration drift across literal `CASES`, local/shared `CHECKS`,
  `step_checks(step)`, `stepN_cases()`, and `get_checks("step-N")` forms;
- mutant files and audit runners disagreeing about `verifier/anti_cheat` paths;
- shell isolation commands that accidentally treated `exec` as the executable;
- a CRDT mutant that was observationally inert after canonical input parsing;
- a CRDT progressive-Oracle defect where patch-only Step 3/4 solutions failed
  and the task audit incorrectly substituted the Step 5 solution;
- DNS owner/type ambiguity, SOA apex derivation, and an unobservable mutant;
- a PCAP nested byte-literal escaping defect;
- a PNG template substitution failure caused by braces inside generated cases;
- WASM exception/interpreter/payload-path drift;
- a systemd fixture that behaved differently on case-insensitive filesystems.

Repairs are narrow, deterministic, and recorded under `evidence/repairs/`.
Failed/intermediate candidates remain outside the expert task directory.

## Final local result

- 10 five-Step Greenfield tasks;
- 409 statically named black-box checks;
- 50/50 Oracle Steps pass;
- 50/50 independently reconstructed cumulative public smokes pass;
- 50/50 progressive Starter states fail the strict release gate;
- 50/50 Step-specific mutants are rejected;
- 10/10 isolation probes pass;
- two clean-copy audits per task have deterministic report hashes;
- sanitation scans report no secret, raw IP endpoint, host-user path, or bytecode
  findings;
- the original frozen handoff still verifies 4,452/4,452 files.

This demonstrates the synthesis and verifier-audit portions of the Data Infra.
It does not demonstrate difficulty calibration. Harbor container baselines,
target-agent rollouts, independent model-family repeats, and expert
semantic/license approval remain explicit downstream gates.

## Independent-audit hardening

The first QA version repeated each task's own audit and therefore shared its
assumptions. Expert review exposed the CRDT false positive: the real cumulative
result was 48/50 public smokes. The hardened QA now independently creates a fresh
workspace for every Step, executes solution Steps 1..N, runs that Step's public
smoke, and runs the strict verifier without calling `run_audit.py`.

It also parses verifier declarations independently and confirms exactly 409
named checks, 50 public smokes, and five mutants covering Steps 1–5 per task.
Before/after CRDT evidence and the deterministic repair operator are included
in the handoff.
