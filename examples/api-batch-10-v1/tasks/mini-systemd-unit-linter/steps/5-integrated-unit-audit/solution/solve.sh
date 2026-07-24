#!/usr/bin/env sh
set -eu
: "${TDF_WORKSPACE:?}"
mkdir -p "$TDF_WORKSPACE/environment/codebase/mini_systemd_unit_linter"
cp "$(dirname "$0")/files/environment/codebase/mini_systemd_unit_linter/policy.py" "$TDF_WORKSPACE/environment/codebase/mini_systemd_unit_linter/policy.py"
