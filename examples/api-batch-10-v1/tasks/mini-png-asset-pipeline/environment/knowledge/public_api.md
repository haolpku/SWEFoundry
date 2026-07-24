# Public API contract

Package: `png_asset_pipeline`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-png-chunks

Public API:
- `class PngChunk:`
- `def parse_png_chunks(data: bytes) -> list[PngChunk]`

Public behavior cases:
- `minimal-png-chunks`
- `bad-signature-raises`

## Step 2: 2-verify-crc-and-chunk-invariants

Public API:
- `class PngProblem:`
- `def validate_png_chunks(chunks: list[PngChunk]) -> list[PngProblem]`

Public behavior cases:
- `crc-mismatch-reported`
- `idat-before-ihdr-reported`

## Step 3: 3-extract-deterministic-asset-metadata

Public API:
- `class PngMetadata:`
- `def extract_png_metadata(chunks: list[PngChunk]) -> PngMetadata`

Public behavior cases:
- `ihdr-dimensions-extracted`
- `text-key-sorted`

## Step 4: 4-plan-deterministic-png-cleanup

Public API:
- `class PngCleanupAction:`
- `def plan_png_cleanup(chunks: list[PngChunk]) -> list[PngCleanupAction]`

Public behavior cases:
- `duplicate-text-removal-planned`
- `clean-png-empty-plan`

## Step 5: 5-integrated-png-audit

Public API:
- `class PngAuditReport:`
- `def audit_png(data: bytes) -> PngAuditReport`

Public behavior cases:
- `valid-png-audit`
- `corrupt-ancillary-audit`
