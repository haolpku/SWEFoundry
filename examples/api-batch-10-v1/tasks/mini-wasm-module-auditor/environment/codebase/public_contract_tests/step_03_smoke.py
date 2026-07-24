#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from wasm_auditor import parse_wasm_sections, validate_wasm_structure

def sec(i, p):
    return bytes([i, len(p)]) + p

base = b'\x00asm\x01\x00\x00\x00'
problems = validate_wasm_structure(parse_wasm_sections(base + sec(1, b'\x00') + sec(1, b'\x00')))
assert any(p.code == 'duplicate-section' for p in problems)
problems = validate_wasm_structure(parse_wasm_sections(base + sec(7, b'\x01\x03run\x00\x00')))
assert any(p.code == 'export-index' for p in problems)
