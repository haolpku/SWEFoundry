#!/bin/sh
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
env -u PYTHONPATH -u PYTHONHOME python3 -I "$DIR/verifier.py"
