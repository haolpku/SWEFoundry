#!/bin/sh
set -eu
workspace="${SWEFOUNDRY_WORKSPACE:-/app/workspace}"
cp "$(dirname "$0")/files/routekit.py" "$workspace/routekit.py"
