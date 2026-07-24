Public smoke tests for mini-crdt-notebook-engine.

These tests exercise the agent-visible public contract only. Each smoke inserts the environment/codebase directory into sys.path before importing crdtnotebook so the candidate package is imported as a black-box library.

Files step_01_smoke.py through step_05_smoke.py correspond to the five public contract steps.
