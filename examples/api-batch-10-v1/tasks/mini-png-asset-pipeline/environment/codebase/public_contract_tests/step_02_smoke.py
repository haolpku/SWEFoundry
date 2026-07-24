#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from png_asset_pipeline import parse_png_chunks, validate_png_chunks

SIG = b'\x89PNG\r\n\x1a\n'

def chunk(t, data=b'', crc=None):
    return struct.pack('>I', len(data)) + t.encode('ascii') + data + struct.pack('>I', (zlib.crc32(t.encode('ascii') + data) & 0xffffffff) if crc is None else crc)

ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
corrupt = SIG + chunk('IHDR', ihdr) + chunk('tEXt', b'Author\x00Ada', crc=0) + chunk('IEND')
problems = validate_png_chunks(parse_png_chunks(corrupt))
assert any(p.code == 'CRC_MISMATCH' and p.chunk_type == 'tEXt' for p in problems)
misordered = SIG + chunk('IDAT', b'abc') + chunk('IHDR', ihdr) + chunk('IEND')
problems = validate_png_chunks(parse_png_chunks(misordered))
assert any(p.code in {'IDAT_BEFORE_IHDR', 'CHUNK_BEFORE_IHDR', 'IHDR_NOT_FIRST'} for p in problems)
