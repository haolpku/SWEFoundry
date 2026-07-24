#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import os
from pathlib import Path
workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()
sys.path.insert(0, str(workspace / 'verifier'))
from common import resolve_context, run_cases, write_outputs
from cases import step3_cases

workspace, tests_dir, reward_dir = resolve_context(__file__)
checks = run_cases('step-3', step3_cases(), workspace, reward_dir)
write_outputs('step-3', checks, reward_dir)
