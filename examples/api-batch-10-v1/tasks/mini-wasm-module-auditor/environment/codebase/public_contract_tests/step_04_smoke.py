#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from wasm_auditor import parse_wasm_sections, plan_wasm_migration

def name(s):
    b = s.encode('utf-8')
    return bytes([len(b)]) + b

def sec(i, p):
    return bytes([i, len(p)]) + p

base = b'\x00asm\x01\x00\x00\x00'
advice = plan_wasm_migration(parse_wasm_sections(base + sec(0, name('x-private'))))
assert any(a.category == 'unknown-custom-section' and a.target == 'x-private' for a in advice)
advice = plan_wasm_migration(parse_wasm_sections(base + sec(0, name('zzz')) + sec(0, name('name'))))
assert any(a.category == 'canonical-name-section' for a in advice)
