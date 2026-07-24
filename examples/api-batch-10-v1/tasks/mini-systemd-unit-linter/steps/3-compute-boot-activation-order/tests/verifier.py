#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
from verifier.checks import get_checks
from verifier.common import run_verifier

if __name__ == '__main__':
    run_verifier('step-3', get_checks('step-3'))
