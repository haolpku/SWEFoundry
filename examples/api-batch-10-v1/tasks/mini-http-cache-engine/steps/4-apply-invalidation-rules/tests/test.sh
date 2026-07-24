#!/bin/sh
set -eu
if [ -z "${TDF_WORKSPACE:-}" ]; then
  TDF_WORKSPACE=$(cd "$(dirname "$0")/../../.." && pwd)
fi
if [ -z "${TDF_TESTS_DIR:-}" ]; then
  TDF_TESTS_DIR=$(cd "$(dirname "$0")" && pwd)
fi
if [ -z "${TDF_REWARD_DIR:-}" ]; then
  TDF_REWARD_DIR=$TDF_TESTS_DIR
fi
export TDF_WORKSPACE TDF_TESTS_DIR TDF_REWARD_DIR
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH PYTHONHOME
env -u PYTHONPATH -u PYTHONHOME python3 -I "$TDF_TESTS_DIR/verifier.py"
