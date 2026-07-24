#!/bin/sh
set -eu
DIR=$(cd "$(dirname "$0")" && pwd)
: "${TDF_WORKSPACE:=$(cd "$DIR/../../.." && pwd)}"
export TDF_WORKSPACE
export TDF_TESTS_DIR="${TDF_TESTS_DIR:-$DIR}"
export TDF_REWARD_DIR="${TDF_REWARD_DIR:-$DIR}"
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
unset PYTHONHOME
env -u PYTHONPATH -u PYTHONHOME python3 -I "$DIR/verifier.py"
