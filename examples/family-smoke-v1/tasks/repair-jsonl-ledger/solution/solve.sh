#!/bin/sh
set -eu
workspace="${SWEFOUNDRY_WORKSPACE:-/app/workspace}"
cp "$(dirname "$0")/files/jsonl_ledger.py" "$workspace/jsonl_ledger.py"
