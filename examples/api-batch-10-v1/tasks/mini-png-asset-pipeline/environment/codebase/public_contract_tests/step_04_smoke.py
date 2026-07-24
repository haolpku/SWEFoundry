#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from png_asset_pipeline import parse_png_chunks, plan_png_cleanup

SIG = b'\x89PNG\r\n\x1a\n'

def chunk(t, data=b'', crc=None):
    return struct.pack('>I', len(data)) + t.encode('ascii') + data + struct.pack('>I', (zlib.crc32(t.encode('ascii') + data) & 0xffffffff) if crc is None else crc)

ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
clean = SIG + chunk('IHDR', ihdr) + chunk('IDAT', b'abc') + chunk('IEND')
assert plan_png_cleanup(parse_png_chunks(clean)) == []
dup = SIG + chunk('IHDR', ihdr) + chunk('tEXt', b'Author\x00Ada') + chunk('tEXt', b'Author\x00Lovelace') + chunk('IEND')
actions = plan_png_cleanup(parse_png_chunks(dup))
assert any(a.action == 'remove' and a.chunk_type == 'tEXt' and 'duplicate' in a.reason for a in actions)
