#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH PYTHONHOME
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
: "${TDF_WORKSPACE:=$ROOT}"
: "${TDF_TESTS_DIR:=$ROOT}"
: "${TDF_REWARD_DIR:=$TDF_WORKSPACE/reward/step-3}"
export TDF_WORKSPACE TDF_TESTS_DIR TDF_REWARD_DIR
env -u PYTHONPATH -u PYTHONHOME python3 -I "$(dirname -- "$0")/verifier.py"
