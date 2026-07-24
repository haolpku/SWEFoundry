#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from wasm_auditor import audit_wasm

def name(s):
    b = s.encode('utf-8')
    return bytes([len(b)]) + b

def sec(i, p):
    return bytes([i, len(p)]) + p

base = b'\x00asm\x01\x00\x00\x00'
valid = base + sec(3, b'\x01\x00') + sec(7, b'\x01' + name('run') + b'\x00\x00') + sec(10, b'\x01\x02\x00\x0b')
report = audit_wasm(valid)
assert report.problems == ()
assert any(s.kind == 'export-function' and s.name == 'run' for s in report.symbols)
invalid = audit_wasm(base + sec(7, b'\x01' + name('run') + b'\x00\x00'))
assert invalid.problems
