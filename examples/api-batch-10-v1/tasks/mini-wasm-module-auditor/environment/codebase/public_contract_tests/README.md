Public smoke tests for mini-wasm-module-auditor.

Run each file with Python from any working directory. Each smoke inserts the codebase directory that contains wasm_auditor into sys.path before importing the candidate package. These tests intentionally cover only the published contract examples; the step verifiers disclose the complete named black-box behavioral gates used for release decisions.
