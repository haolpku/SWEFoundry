# Public API contract

Package: `mini_systemd_unit_linter`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-unit-files-deterministically

Public API:
- `class UnitFile:`
- `def load_units(paths: list[str]) -> list[UnitFile]`

Public behavior cases:
- `service-with-install-loads`
- `duplicate-execstart-raises`

## Step 2: 2-validate-dependency-integrity

Public API:
- `class UnitProblem:`
- `def validate_unit_graph(units: list[UnitFile]) -> list[UnitProblem]`

Public behavior cases:
- `missing-required-unit-reported`
- `wanted-missing-unit-warning`

## Step 3: 3-compute-boot-activation-order

Public API:
- `class DependencyCycleError(Exception):`
- `def plan_activation(units: list[UnitFile], target: str) -> list[str]`

Public behavior cases:
- `simple-after-order`
- `cycle-raises-with-witness`

## Step 4: 4-replay-failure-recovery

Public API:
- `class BootReplay:`
- `def replay_activation(units: list[UnitFile], plan: list[str], failed: set[str]) -> BootReplay`

Public behavior cases:
- `required-failure-skips-dependent`
- `wanted-failure-continues`

## Step 5: 5-integrated-unit-audit

Public API:
- `class UnitAuditReport:`
- `def audit_units(paths: list[str], target: str, failed: set[str]) -> UnitAuditReport`

Public behavior cases:
- `healthy-boot-audit`
- `cycle-audit-reports-error`
