# Data Infra API Batch 10 — Expert Review Handoff

This is a new ten-task batch produced by the operator-style Data Infra and the
configured OpenAI-compatible API. It is independent of, and does not modify,
the frozen original ten-task buyer handoff.

## What is proven

- 10/10 five-Step Greenfield Harbor-format tasks materialized;
- 409 statically named black-box behavior checks;
- 50/50 Oracle Steps pass;
- 50/50 cumulative public-contract smokes pass;
- 50/50 progressive Starter states are rejected;
- 50/50 deterministic Step-specific mutants are rejected, including Step 5;
- 10/10 Python isolation probes pass;
- two clean-copy audit repeats per task produce identical reports;
- secret, raw IP endpoint, host-user path, and Python bytecode scans are clean;
- the original handoff Manifest still verifies 4,452/4,452 files.

## Task portfolio

| Task | Concept source license | Checks | Mutants rejected |
|---|---|---:|---:|
| `mini-crdt-notebook-engine` | MIT | 41 | 5/5 |
| `mini-dns-zone-auditor` | IETF Trust Legal Provisions | 43 | 5/5 |
| `mini-http-cache-engine` | IETF Trust Legal Provisions | 43 | 5/5 |
| `mini-ical-sync-engine` | IETF Trust Legal Provisions | 41 | 5/5 |
| `mini-mqtt-session-broker` | EPL-2.0 | 42 | 5/5 |
| `mini-pcap-stream-reassembler` | BSD-3-Clause | 41 | 5/5 |
| `mini-png-asset-pipeline` | W3C Document License | 43 | 5/5 |
| `mini-posix-manifest-installer` | Open Group Base Specifications Issue 7 terms | 36 | 5/5 |
| `mini-systemd-unit-linter` | LGPL-2.1-or-later | 38 | 5/5 |
| `mini-wasm-module-auditor` | Apache-2.0 | 41 | 5/5 |

## Status boundary

These tasks are `verifier-audited` expert-review candidates. They are not
`release-ready`: Harbor Oracle/Nop container jobs, target-agent rollout,
cross-model-family difficulty calibration, and expert semantic/license approval
remain open. No T5/H4 or stable pass@1 claim is made.

## Review entry points

- `tasks/`: the ten self-contained task candidates, including starter,
  knowledge, five instructions, five solutions, verifiers, anti-cheat mutants,
  and audit reports;
- `evidence/BATCH_QA.json`: uniform ten-task repeatability and sanitation QA;
- `evidence/generation/`: sanitized API worker summaries and operator ledger;
- `evidence/repairs/`: deterministic repair scripts/records for failures caught
  by the gates;
- `infra/`: operator catalog, scaling plan, prompts, compiler, normalizer,
  materializer, and QA implementation used for this experiment;
- `infra/batch/P0_CRDT_REPAIR_REPORT.md`: reproduction, root cause, repair, and
  before/after evidence for the expert-found CRDT defect;
- `TASK_CATALOG.json`: machine-readable portfolio and open-gate summary;
- `HOW_TO_VERIFY.md`: copy-paste integrity, single-task, and whole-batch checks;
- `MANIFEST.sha256`: integrity list for the complete handoff.

API credentials are never persisted. Endpoint values in retained evidence are
redacted placeholders.
