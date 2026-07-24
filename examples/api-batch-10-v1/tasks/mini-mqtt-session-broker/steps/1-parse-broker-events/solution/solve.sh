#!/bin/sh
set -eu
: "${TDF_WORKSPACE:=$(pwd)}"
cd "$(dirname "$0")/files"
find environment -type f | sort | while IFS= read -r file; do
  mkdir -p "$TDF_WORKSPACE/$(dirname "$file")"
  cp "$file" "$TDF_WORKSPACE/$file"
done
