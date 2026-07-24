Return exactly one valid JSON object and no Markdown:

{
  "schema_version": "1.0",
  "task_id": "<exact task_id from accepted blueprint>",
  "fragment": "verification",
  "files": [
    {"path": "relative/path", "executable": false, "content": "complete file"}
  ],
  "implementation_notes": [],
  "known_open_gates": []
}

Generate the full black-box verification fragment for the supplied blueprint,
public contract, and generated core fragment.

Include:

- exactly five public smoke files named
  `environment/codebase/public_contract_tests/step_01_smoke.py` through
  `step_05_smoke.py`, plus README;
- each smoke inserts its codebase parent into `sys.path` before importing the
  candidate, and succeeds on the complete Oracle;
- exactly five Step directories matching the core fragment, each containing
  `instruction.md`, executable `tests/test.sh`, and `tests/verifier.py`;
- shared verifier helpers under `verifier/`;
- exactly five executable deterministic mutant scripts named with prefixes
  `fp1_` through `fp5_`, each targeting its corresponding Step;
- executable `verifier/run_audit.py`.

Every Step verifier:

- uses only black-box behavior, never candidate source inspection;
- launches candidate cases with Python `-I`;
- sets `sys.dont_write_bytecode = True` before importing shared helpers;
- honors `TDF_WORKSPACE`, `TDF_TESTS_DIR`, and `TDF_REWARD_DIR`;
- removes `PYTHONPATH` and `PYTHONHOME`;
- writes reward.txt, reward.json, evidence.json and ctrf.json;
- exposes exactly correctness, code_quality, reasoning, efficiency,
  weighted_total and release_pass;
- sets release_pass to 1 only when correctness is exactly 1.0;
- has at least seven named behavioral checks including a read-only state check.

Step 5 adds integrated recovery/migration semantics and critical regressions
for Steps 1-4. Hidden names must all be disclosed in the contract.

The audit runner must:

- create temporary workspaces from `environment/codebase`;
- before each cumulative solution, prove that Step's Starter release_pass is 0;
- after each cumulative solution, prove that Step's Oracle release_pass is 1;
- apply every mutant to a complete Oracle and run its corresponding Step
  verifier, proving release_pass is 0;
- probe `sitecustomize.py` and PYTHONPATH isolation;
- set PYTHONDONTWRITEBYTECODE=1;
- write a stable sorted `verifier/audit-report.json` without temporary paths,
  timestamps, durations, or random IDs;
- exit nonzero unless every gate passes.

Mutants must match the actual complete Oracle text or behavior mechanically;
check exact quote/format patterns against the core fragment. No random, hash(),
time, UUID, network, timing race, flaky order, or source-introspection tests.
