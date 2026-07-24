#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORKSPACE=${TDF_WORKSPACE:-$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)}
export TDF_WORKSPACE="$WORKSPACE"
export TDF_TESTS_DIR="${TDF_TESTS_DIR:-$SCRIPT_DIR}"
export TDF_REWARD_DIR="${TDF_REWARD_DIR:-$WORKSPACE/rewards/step-4}"
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH PYTHONHOME
env -u PYTHONPATH -u PYTHONHOME python3 -I "$SCRIPT_DIR/verifier.py"
