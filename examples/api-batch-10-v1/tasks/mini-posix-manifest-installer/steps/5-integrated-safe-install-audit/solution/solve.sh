#!/bin/sh
set -eu
workspace=${TDF_WORKSPACE:-$(pwd)}
mkdir -p "$workspace/environment/codebase/posix_manifest_installer"
cp "$workspace/steps/5-integrated-safe-install-audit/solution/files/posix_manifest_installer/installer.py" "$workspace/environment/codebase/posix_manifest_installer/installer.py"
