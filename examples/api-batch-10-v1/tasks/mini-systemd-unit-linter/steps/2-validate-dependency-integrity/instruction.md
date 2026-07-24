# Step 2 verification contract

Validate dependency edges against loaded units only. The verifier is black-box and checks these disclosed names: requires_missing_is_error, wants_missing_is_warning, edge_type_severity_and_problem_ordering, root_confinement_loaded_units_only, known_dependencies_are_silent, duplicate_parse_regression, read_only_state_check.

Expected public API: class UnitProblem and def validate_unit_graph(units: list[UnitFile]) -> list[UnitProblem].

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_02_smoke.py`.
