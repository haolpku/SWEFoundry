#!/usr/bin/env python3
import os
import sys
sys.dont_write_bytecode = True
os.environ.pop('PYTHONPATH', None)
os.environ.pop('PYTHONHOME', None)
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from verifier.common import run_verification
raise SystemExit(run_verification(4))
