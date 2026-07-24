#!/bin/sh
set -eu
ROOT="${TDF_WORKSPACE:-$(pwd)}"
SRC="$ROOT/steps/1-canonicalize-requests-and-responses/solution/files"
DST="$ROOT/environment/codebase/mini_http_cache_engine"
cp "$SRC/core.py" "$DST/core.py"
python3 -m py_compile "$DST/core.py"
