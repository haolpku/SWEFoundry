#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from png_asset_pipeline import extract_png_metadata, parse_png_chunks

SIG = b'\x89PNG\r\n\x1a\n'

def chunk(t, data=b''):
    return struct.pack('>I', len(data)) + t.encode('ascii') + data + struct.pack('>I', zlib.crc32(t.encode('ascii') + data) & 0xffffffff)

png = SIG + chunk('IHDR', struct.pack('>IIBBBBB', 7, 5, 8, 2, 0, 0, 0)) + chunk('tEXt', b'Zed\x00last') + chunk('tEXt', b'Alpha\x00first') + chunk('IDAT', b'not-inflated') + chunk('IEND')
meta = extract_png_metadata(parse_png_chunks(png))
assert (meta.width, meta.height, meta.compression_method) == (7, 5, 0)
assert list(meta.text.keys()) == ['Alpha', 'Zed']
