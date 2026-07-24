#!/usr/bin/env sh
set -eu
if [ -z "${TDF_WORKSPACE+x}" ]; then TDF_WORKSPACE="$(pwd)"; export TDF_WORKSPACE; fi
TDF_TESTS_DIR="${TDF_TESTS_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"; export TDF_TESTS_DIR
TDF_REWARD_DIR="${TDF_REWARD_DIR:-$TDF_WORKSPACE/reward}"; export TDF_REWARD_DIR
PYTHONDONTWRITEBYTECODE=1; export PYTHONDONTWRITEBYTECODE
env -u PYTHONPATH -u PYTHONHOME python3 -I "$TDF_TESTS_DIR/verifier.py"
