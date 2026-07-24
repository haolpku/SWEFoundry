#!/bin/sh
set -eu
: "${TDF_WORKSPACE:=$(pwd)}"
SRC=$(CDPATH= cd -- "$(dirname -- "$0")/files" && pwd)
mkdir -p "$TDF_WORKSPACE/environment/codebase/png_asset_pipeline"
cp "$SRC/environment/codebase/png_asset_pipeline/metadata.py" "$TDF_WORKSPACE/environment/codebase/png_asset_pipeline/metadata.py"
cp "$SRC/environment/codebase/png_asset_pipeline/__init__.py" "$TDF_WORKSPACE/environment/codebase/png_asset_pipeline/__init__.py"
