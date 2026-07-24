#!/usr/bin/env python3
import os
import pathlib
import sys

sys.dont_write_bytecode = True
TESTS_DIR = pathlib.Path(os.environ.get('TDF_TESTS_DIR', pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(TESTS_DIR))

from verifier.checks import CHECKS
from verifier.helpers import run_step

raise SystemExit(run_step('step-1', CHECKS['step-1']))
