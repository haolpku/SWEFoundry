#!/usr/bin/env sh
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=${TDF_WORKSPACE:-$(CDPATH= cd -- "$DIR/../../.." && pwd)}
export TDF_WORKSPACE=$ROOT
export TDF_TESTS_DIR=${TDF_TESTS_DIR:-$DIR}
export TDF_REWARD_DIR=${TDF_REWARD_DIR:-$DIR/reward}
export PYTHONDONTWRITEBYTECODE=1
env -u PYTHONPATH -u PYTHONHOME "${TDF_PYTHON:-python3}" -I "$DIR/verifier.py"
