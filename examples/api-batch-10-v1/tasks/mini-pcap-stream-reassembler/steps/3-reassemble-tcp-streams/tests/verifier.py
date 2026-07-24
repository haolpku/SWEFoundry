#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from verifier.harness import run_step
from verifier.step_checks import get_checks

if __name__ == '__main__':
    raise SystemExit(run_step('step-3', get_checks('step-3')))
