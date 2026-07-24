# Public API contract

Package: `dns_zone_auditor`

Hidden tests may exercise only names and observable behavior disclosed here.

## Step 1: 1-parse-zone-master-files

Public API:
- `class DnsRecord:`
- `def parse_zone(text: str, origin: str) -> list[DnsRecord]`

Public behavior cases:
- `origin-relative-names`
- `txt-with-spaces`

## Step 2: 2-validate-zone-integrity

Public API:
- `class ZoneProblem:`
- `def validate_zone(records: list[DnsRecord]) -> list[ZoneProblem]`

Public behavior cases:
- `cname-conflict-reported`
- `missing-apex-ns-reported`

## Step 3: 3-simulate-offline-dns-answers

Public API:
- `class DnsAnswer:`
- `def answer_zone(records: list[DnsRecord], qname: str, qtype: str) -> DnsAnswer`

Public behavior cases:
- `a-record-answer`
- `cname-chain-answer`

## Step 4: 4-plan-serial-and-digest-migration

Public API:
- `class ZoneMigration:`
- `def plan_zone_migration(records: list[DnsRecord], target_ttl: int) -> ZoneMigration`

Public behavior cases:
- `serial-increment-planned`
- `already-normalized-empty-changes`

## Step 5: 5-integrated-zone-audit

Public API:
- `class ZoneAuditReport:`
- `def audit_zone(text: str, origin: str, queries: list[tuple[str, str]], target_ttl: int) -> ZoneAuditReport`

Public behavior cases:
- `healthy-zone-audit`
- `broken-zone-audit-with-query`
