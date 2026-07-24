# API batch 10 v1

This batch is isolated from:

- the frozen ten-task buyer handoff;
- `multistep_v1/tasks/`;
- the `mini-transit-ledger` API synthesis pilot.

Every candidate begins as `under-construction`. A task may enter the expert
review package only after deterministic static validation, progressive
Starter/Oracle audit, five Step-specific mutant rejections, isolation probing,
repeatability checks, and sensitive-data scanning.

The experiment completed all of those local gates for 10/10 candidates. The
expert handoff promotes copies to `verifier-audited`; source candidates remain
the pre-handoff production artifacts. Harbor container execution, target-agent
rollout, cross-family difficulty calibration, and expert semantic/license
approval remain open.

See `DATA_INFRA_EFFECT.md` for measured API usage, failures caught by the gates,
and the exact boundary of the result.
