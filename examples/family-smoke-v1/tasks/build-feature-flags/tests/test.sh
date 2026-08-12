#!/bin/sh
set -eu
python3 /tests/verifier.py
sync
sleep 1
