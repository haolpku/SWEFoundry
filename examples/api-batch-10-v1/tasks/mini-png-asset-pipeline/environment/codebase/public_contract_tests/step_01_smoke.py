#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from png_asset_pipeline import parse_png_chunks

SIG = b'\x89PNG\r\n\x1a\n'

def chunk(t, data=b''):
    return struct.pack('>I', len(data)) + t.encode('ascii') + data + struct.pack('>I', zlib.crc32(t.encode('ascii') + data) & 0xffffffff)

png = SIG + chunk('IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk('IDAT', b'abc') + chunk('IEND')
chunks = parse_png_chunks(png)
assert [c.type for c in chunks] == ['IHDR', 'IDAT', 'IEND']
try:
    parse_png_chunks(b'not a png')
except ValueError:
    pass
else:
    raise AssertionError('bad signature must raise ValueError')
