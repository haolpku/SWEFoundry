#!/usr/bin/env sh
set -eu
ROOT="${TDF_WORKSPACE:-$(pwd)}"
SRC="$(CDPATH= cd -- "$(dirname -- "$0")/files" && pwd)"
mkdir -p "$ROOT/environment/codebase/mini_ical_sync_engine"
cp "$SRC/environment/codebase/mini_ical_sync_engine/engine.py" "$ROOT/environment/codebase/mini_ical_sync_engine/engine.py"
