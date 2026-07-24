#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from png_asset_pipeline import audit_png

SIG = b'\x89PNG\r\n\x1a\n'

def chunk(t, data=b'', crc=None):
    return struct.pack('>I', len(data)) + t.encode('ascii') + data + struct.pack('>I', (zlib.crc32(t.encode('ascii') + data) & 0xffffffff) if crc is None else crc)

ihdr = struct.pack('>IIBBBBB', 2, 3, 8, 2, 0, 0, 0)
valid = SIG + chunk('IHDR', ihdr) + chunk('tEXt', b'Title\x00Smoke') + chunk('IDAT', b'abc') + chunk('IEND')
report = audit_png(valid)
assert report.parse_error is None
assert report.metadata.width == 2 and report.metadata.height == 3
corrupt = SIG + chunk('IHDR', ihdr) + chunk('tEXt', b'Title\x00Smoke', crc=0) + chunk('IEND')
report = audit_png(corrupt)
assert any(p.code == 'CRC_MISMATCH' for p in report.problems)
assert any(a.action == 'repair_crc' for a in report.cleanup_actions)
