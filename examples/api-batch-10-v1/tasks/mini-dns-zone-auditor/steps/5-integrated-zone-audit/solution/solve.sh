#!/usr/bin/env sh
set -eu
workspace="${TDF_WORKSPACE:-$(pwd)}"
target="$workspace/environment/codebase/dns_zone_auditor"
mkdir -p "$target"
cp "$(dirname "$0")/files/dns_zone_auditor/audit.py" "$target/audit.py"
python3 -m py_compile "$target/audit.py"
