# Architecture and semantic boundaries

Build PNG Asset Integrity and Deterministic Transcoding Planner as an offline, deterministic Python system in five progressive implementation steps.

The candidate is an offline concept study. State, ordering, validation, and recovery behavior must be deterministic and observable through the published API. Candidate implementations must not depend on network availability, process-salted hashing, wall-clock time, locale, UUIDs, or host directory ordering.

## Step 1: 1-parse-png-chunks

Parse PNG signature and chunks from bytes, return chunk records in file order, validate length boundaries and IEND termination, and raise ValueError for missing signature or truncated chunk data.

Verifier semantic categories:
- chunk length bounds
- IEND termination
- file-order preservation

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 2: 2-verify-crc-and-chunk-invariants

Verify CRC32 for every chunk and validate IHDR, PLTE, IDAT, and IEND ordering constraints, returning PngProblem objects sorted by chunk offset and diagnostic code.

Verifier semantic categories:
- CRC calculation
- critical chunk order
- singleton chunks

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 3: 3-extract-deterministic-asset-metadata

Extract IHDR fields and supported text metadata into canonical key order, reject invalid compression method values with ValueError, and do not inflate or decode image IDAT data.

Verifier semantic categories:
- metadata canonicalization
- compression method validation
- no image decode

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 4: 4-plan-deterministic-png-cleanup

Plan read-only cleanup actions for duplicate metadata, unsafe ancillary chunks, palette normalization, and CRC repair, returning idempotent actions while distinguishing critical chunks that cannot be safely removed.

Verifier semantic categories:
- idempotent planning
- ancillary safety
- action ordering

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.

## Step 5: 5-integrated-png-audit

Integrate chunk parsing, CRC validation, metadata extraction, and cleanup planning into PngAuditReport, preserve steps 1 through 4 outputs, and provide deterministic truncated-write recovery guidance.

Verifier semantic categories:
- steps 1-4 regression
- integrity reporting
- read-only validation

The Step solution is applied cumulatively. Previously published behavior remains part of the final system contract.
