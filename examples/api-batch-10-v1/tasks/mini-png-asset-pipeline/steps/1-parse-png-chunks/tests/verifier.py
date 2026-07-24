#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import os
from pathlib import Path
root = Path(os.environ.get('TDF_TESTS_DIR', Path(__file__).resolve().parents[3])).resolve()
sys.path.insert(0, str(root))
from verifier.common import CHECKS, run_step_verifier
_DECLARED_CHECKS = CHECKS['step-1']
# Shared runner writes "release_pass" only when correctness == 1.0 and launches cases with "-I".
if __name__ == '__main__':
    raise SystemExit(run_step_verifier('step-1', root))
