#!/bin/sh
set -eu
workspace="${SWEFOUNDRY_WORKSPACE:-/app/workspace}"
mkdir -p "$workspace/featureflags"
cp "$(dirname "$0")/files/featureflags/__init__.py" "$workspace/featureflags/__init__.py"
