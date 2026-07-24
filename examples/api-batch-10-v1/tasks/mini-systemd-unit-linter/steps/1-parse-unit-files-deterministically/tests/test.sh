#!/usr/bin/env sh
set -eu
: "${TDF_WORKSPACE:?}"
: "${TDF_TESTS_DIR:?}"
: "${TDF_REWARD_DIR:?}"
mkdir -p "$TDF_REWARD_DIR"
unset PYTHONPATH
unset PYTHONHOME
export PYTHONDONTWRITEBYTECODE=1
exec env -u PYTHONPATH -u PYTHONHOME python3 -I "$(dirname "$0")/verifier.py"
