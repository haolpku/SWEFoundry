#!/usr/bin/env sh
set -eu
ROOT="${TDF_WORKSPACE:-$(pwd)}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC="$SCRIPT_DIR/files/wasm_auditor"
DST="$ROOT/environment/codebase/wasm_auditor"
mkdir -p "$DST"
for f in validation.py __init__.py; do
  tmp="$DST/.$f.tmp"
  cp "$SRC/$f" "$tmp"
  chmod 0644 "$tmp"
  mv "$tmp" "$DST/$f"
done
