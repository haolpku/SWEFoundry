#!/bin/sh
set -eu
export TDF_WORKSPACE=${TDF_WORKSPACE:-$(pwd)}
if [ -z "${TDF_TESTS_DIR:-}" ]; then
  TDF_TESTS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
  export TDF_TESTS_DIR
fi
export TDF_REWARD_DIR=${TDF_REWARD_DIR:-$TDF_TESTS_DIR/reward}
mkdir -p "$TDF_REWARD_DIR"
unset PYTHONPATH
unset PYTHONHOME
export PYTHONDONTWRITEBYTECODE=1
env -u PYTHONPATH -u PYTHONHOME python3 -I "$TDF_TESTS_DIR/verifier.py"
