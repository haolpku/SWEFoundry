#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from wasm_auditor import parse_wasm_sections, summarize_wasm_symbols

def leb(n):
    out = []
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

def name(s):
    b = s.encode('utf-8')
    return leb(len(b)) + b

def sec(i, p):
    return bytes([i]) + leb(len(p)) + p

module = b'\x00asm\x01\x00\x00\x00' + sec(3, b'\x01\x00') + sec(7, b'\x01' + name('run') + b'\x00\x00')
symbols = summarize_wasm_symbols(parse_wasm_sections(module))
assert [(s.kind, s.name, s.index) for s in symbols] == [('function', 'function[0]', 0), ('export-function', 'run', 0)]
try:
    bad_import = b'\x01\x01\xff\x01f\x00\x00'
    summarize_wasm_symbols(parse_wasm_sections(b'\x00asm\x01\x00\x00\x00' + sec(2, bad_import)))
except ValueError:
    pass
else:
    raise AssertionError('invalid-name-raises')
