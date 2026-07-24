#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from wasm_auditor import parse_wasm_sections

EMPTY = b'\x00asm\x01\x00\x00\x00'
assert parse_wasm_sections(EMPTY) == []
try:
    parse_wasm_sections(b'bad!\x01\x00\x00\x00')
except ValueError:
    pass
else:
    raise AssertionError('bad-magic-raises')
