#!/usr/bin/env sh
set -eu
ROOT="${TDF_WORKSPACE:-$(pwd)}"
DST="$ROOT/environment/codebase/crdtnotebook"
mkdir -p "$DST"
cp "$(dirname "$0")/files/crdtnotebook/engine.py" "$DST/engine.py"
cp "$(dirname "$0")/files/crdtnotebook/__init__.py" "$DST/__init__.py"
python3 -m py_compile "$DST/engine.py" "$DST/__init__.py"
