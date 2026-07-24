#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import pathlib
_repo_root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_repo_root))
from verifier.common import finish

BASE = "from mini_http_cache_engine import HttpCacheEntry, invalidate_http_cache\ndef e(key, path='/item', query='', cc='max-age=60'):\n    return HttpCacheEntry(key=key, method='GET', scheme='http', host='example.com', path=path, query=query, response_headers={'cache-control': cc})\n"
CHECKS = [
('post_invalidates_all_variants', BASE + r'''
entries = [e('k|fr'), e('k|en')]
r = invalidate_http_cache(entries, {'method': 'POST', 'scheme': 'http', 'host': 'example.com', 'path': '/item'})
print(json.dumps({'ok': r.affected_keys == ['k|en', 'k|fr'] and r.retained_entries == [], 'details': {'affected': r.affected_keys}}))
'''),
('purge_key_only', BASE + r'''
entries = [e('a'), e('b')]
r = invalidate_http_cache(entries, {'type': 'purge', 'key': 'b'})
print(json.dumps({'ok': r.affected_keys == ['b'] and [x.key for x in r.retained_entries] == ['a'], 'details': {'affected': r.affected_keys, 'retained': [x.key for x in r.retained_entries]}}))
'''),
('purge_uri_all_variants', BASE + r'''
entries = [e('v2'), e('v1'), e('other', path='/other')]
r = invalidate_http_cache(entries, {'type': 'purge', 'scheme': 'http', 'host': 'example.com', 'path': '/item'})
print(json.dumps({'ok': r.affected_keys == ['v1', 'v2'] and [x.key for x in r.retained_entries] == ['other'], 'details': {'affected': r.affected_keys}}))
'''),
('no_store_not_retained', BASE + r'''
entries = [e('ok'), e('bad', cc='no-store')]
r = invalidate_http_cache(entries, {'type': 'no-store'})
print(json.dumps({'ok': r.affected_keys == ['bad'] and [x.key for x in r.retained_entries] == ['ok'], 'details': {'affected': r.affected_keys, 'retained': [x.key for x in r.retained_entries]}}))
'''),
('affected_keys_sorted', BASE + r'''
entries = [e('z'), e('a'), e('m')]
r = invalidate_http_cache(entries, {'method': 'DELETE', 'scheme': 'http', 'host': 'example.com', 'path': '/item'})
print(json.dumps({'ok': r.affected_keys == ['a', 'm', 'z'], 'details': {'affected': r.affected_keys}}))
'''),
('safe_get_noop', BASE + r'''
entries = [e('a'), e('b')]
r = invalidate_http_cache(entries, {'method': 'GET', 'scheme': 'http', 'host': 'example.com', 'path': '/item'})
print(json.dumps({'ok': r.affected_keys == [] and [x.key for x in r.retained_entries] == ['a', 'b'], 'details': {'affected': r.affected_keys}}))
'''),
('unaffected_uri_retained', BASE + r'''
entries = [e('hit'), e('miss', path='/other')]
r = invalidate_http_cache(entries, {'method': 'PUT', 'scheme': 'http', 'host': 'example.com', 'path': '/item'})
print(json.dumps({'ok': r.affected_keys == ['hit'] and [x.key for x in r.retained_entries] == ['miss'], 'details': {'affected': r.affected_keys, 'retained': [x.key for x in r.retained_entries]}}))
'''),
('read_only_entries_and_event', BASE + r'''
entries = [e('a'), e('b')]
event = {'method': 'POST', 'scheme': 'http', 'host': 'example.com', 'path': '/item'}
before_entries = [x.__dict__.copy() for x in entries]
before_event = dict(event)
invalidate_http_cache(entries, event)
print(json.dumps({'ok': before_entries == [x.__dict__.copy() for x in entries] and before_event == event, 'details': {}}))
'''),
]

if __name__ == '__main__':
    raise SystemExit(finish('step-4', CHECKS, __file__))
