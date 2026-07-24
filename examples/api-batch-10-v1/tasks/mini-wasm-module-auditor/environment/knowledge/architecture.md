# Architecture and semantic boundaries

Build WebAssembly Binary Module Validator and Migration Reporter as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-read-wasm-binary-sections

Parse the WebAssembly magic, version, and ordered sections from bytes, validate bounded LEB128 lengths and payload boundaries, and raise ValueError for truncated or malformed section encodings.

Verifier semantic categories:
- LEB128 overflow
- truncation handling
- section ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-decode-type-import-and-export-metadata

Decode restricted type, import, function, memory, global, and export sections into deterministic summaries, maintain separate index spaces, and reject invalid UTF-8 names with ValueError.

Verifier semantic categories:
- index space accounting
- UTF-8 validation
- symbol ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-validate-structural-integrity

Validate section order, duplicate singleton sections, function count consistency, export index bounds, and custom-section allowance, returning sorted WasmProblem objects without attempting module execution.

Verifier semantic categories:
- singleton enforcement
- cross-section counts
- custom section placement

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-report-compatibility-migrations

Generate read-only migration advice for unsupported features, deprecated name patterns, and deterministic canonical custom-section ordering, deduplicating equivalent advice while leaving input section payload bytes unchanged.

Verifier semantic categories:
- feature detection
- advice deduplication
- stable ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-wasm-audit

Integrate parsing, symbol decoding, structural validation, and migration advice into WasmAuditReport, preserve steps 1 through 4 outputs, and keep all results read-only, deterministic, and recoverable after malformed sections.

Verifier semantic categories:
- steps 1-4 regression
- binary integrity
- exception consistency

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
