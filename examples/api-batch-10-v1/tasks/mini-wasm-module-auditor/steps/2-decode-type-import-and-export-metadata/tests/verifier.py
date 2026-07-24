#!/usr/bin/env python3
import os
import pathlib
import sys
sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(os.environ.get('TDF_VERIFIER_ROOT', pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(REPO_ROOT))
from verifier.step_runner import CHECKS, main
_DECLARED_CHECKS = CHECKS['step-2']
if __name__ == '__main__':
    raise SystemExit(main(2))
