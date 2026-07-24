#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_http_cache_engine import HttpCacheEntry, merge_http_304

entry = HttpCacheEntry(key='k', method='GET', scheme='http', host='example.com', path='/', query='', response_headers={'etag': '"abc"', 'cache-control': 'max-age=10'}, body='payload')
merged = merge_http_304(entry, {'status': '304', 'ETag': '"abc"', 'Cache-Control': 'max-age=90', 'body': ''})
assert merged.body == 'payload'
assert merged.response_headers['cache-control'] == 'max-age=90'
try:
    merge_http_304(entry, {'status': '304', 'ETag': '"other"'})
except ValueError:
    pass
else:
    raise AssertionError('mismatched ETag must raise ValueError')
print('step_03_smoke ok')
