#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import pathlib
_repo_root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_repo_root))
from verifier.common import finish

BASE = "from mini_http_cache_engine import HttpCacheEntry, merge_http_304\ndef entry():\n    return HttpCacheEntry(key='k', method='GET', scheme='http', host='example.com', path='/', query='', response_headers={'etag': '\"abc\"', 'last-modified': 'Thu, 01 Jan 1970 00:00:00 GMT', 'cache-control': 'max-age=10', 'content-length': '7', 'content-type': 'text/plain'}, body='payload')\n"
CHECKS = [
('etag_304_merge', BASE + r'''
m = merge_http_304(entry(), {'status': '304', 'ETag': '"abc"', 'Cache-Control': 'max-age=90', 'body': ''})
print(json.dumps({'ok': m.body == 'payload' and m.response_headers['cache-control'] == 'max-age=90', 'details': {'body': m.body, 'headers': m.response_headers}}))
'''),
('mismatched_etag_raises', BASE + r'''
try:
    merge_http_304(entry(), {'status': '304', 'ETag': '"other"'})
    ok = False
except ValueError:
    ok = True
print(json.dumps({'ok': ok, 'details': {}}))
'''),
('mismatched_last_modified_raises', BASE + r'''
try:
    merge_http_304(entry(), {'status': '304', 'Last-Modified': 'Fri, 02 Jan 1970 00:00:00 GMT'})
    ok = False
except ValueError:
    ok = True
print(json.dumps({'ok': ok, 'details': {}}))
'''),
('hop_by_hop_not_merged', BASE + r'''
m = merge_http_304(entry(), {'status': '304', 'ETag': '"abc"', 'Connection': 'close', 'Transfer-Encoding': 'chunked'})
print(json.dumps({'ok': 'connection' not in m.response_headers and 'transfer-encoding' not in m.response_headers, 'details': m.response_headers}))
'''),
('content_length_not_replaced', BASE + r'''
m = merge_http_304(entry(), {'status': '304', 'ETag': '"abc"', 'Content-Length': '0', 'Content-Range': 'bytes 0-0/0'})
print(json.dumps({'ok': m.response_headers.get('content-length') == '7' and 'content-range' not in m.response_headers, 'details': m.response_headers}))
'''),
('validator_preserved_when_absent', BASE + r'''
m = merge_http_304(entry(), {'status': '304', 'Cache-Control': 'max-age=20'})
print(json.dumps({'ok': m.response_headers.get('etag') == '"abc"' and m.response_headers.get('last-modified') == 'Thu, 01 Jan 1970 00:00:00 GMT', 'details': m.response_headers}))
'''),
('allowed_metadata_updated', BASE + r'''
m = merge_http_304(entry(), {'status': '304', 'ETag': '"abc"', 'Content-Type': 'application/json', 'Expires': 'Thu, 01 Jan 1970 00:10:00 GMT'})
print(json.dumps({'ok': m.response_headers.get('content-type') == 'application/json' and m.response_headers.get('expires') == 'Thu, 01 Jan 1970 00:10:00 GMT', 'details': m.response_headers}))
'''),
('read_only_entry_and_response', BASE + r'''
e = entry()
r = {'status': '304', 'ETag': '"abc"', 'Cache-Control': 'max-age=90', 'body': ''}
before_e = e.__dict__.copy()
before_r = dict(r)
merge_http_304(e, r)
print(json.dumps({'ok': before_e == e.__dict__ and before_r == r, 'details': {}}))
'''),
]

if __name__ == '__main__':
    raise SystemExit(finish('step-3', CHECKS, __file__))
