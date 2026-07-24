Public contract smoke tests for mini-systemd-unit-linter.

Run each step_XX_smoke.py from any working directory with Python. Each smoke adds the codebase directory to sys.path before importing mini_systemd_unit_linter.

Disclosed behavioral contract names:
- Step 1: service-with-install-loads, duplicate-execstart-raises, canonical unit names, comment handling, duplicate detection, malformed section headers, read-only load state.
- Step 2: missing-required-unit-reported, wanted-missing-unit-warning, edge type severity, root confinement, problem ordering, known dependency suppression, read-only validation state.
- Step 3: simple-after-order, cycle-raises-with-witness, cycle determinism, conflict exclusion, target closure, Before ordering, canonical topological order, read-only planning state.
- Step 4: required-failure-skips-dependent, wanted-failure-continues, failure propagation, restart limit semantics, canonical set output, unknown plan entries, read-only replay state.
- Step 5: healthy-boot-audit, cycle-audit-reports-error, steps 1-4 regression, read-only validation, exception mapping, integrated recovery summaries, migration-preserving audit outputs.
