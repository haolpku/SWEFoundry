#!/usr/bin/env sh
set -eu
ROOT="${TDF_WORKSPACE:-$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)}"
TESTS="${TDF_TESTS_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)}"
REWARD="${TDF_REWARD_DIR:-$ROOT/reward/step-5}"
mkdir -p "$REWARD"
exec env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 TDF_WORKSPACE="$ROOT" TDF_TESTS_DIR="$TESTS" TDF_REWARD_DIR="$REWARD" python3 -I "$(dirname -- "$0")/verifier.py"
