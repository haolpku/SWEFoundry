#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_http_cache_engine import HttpCacheEntry, invalidate_http_cache

e1 = HttpCacheEntry(key='k|a', method='GET', scheme='http', host='example.com', path='/item', query='', vary=('accept-language',), request_headers={'accept-language': 'en'})
e2 = HttpCacheEntry(key='k|b', method='GET', scheme='http', host='example.com', path='/item', query='', vary=('accept-language',), request_headers={'accept-language': 'fr'})
result = invalidate_http_cache([e2, e1], {'method': 'POST', 'scheme': 'http', 'host': 'example.com', 'path': '/item'})
assert result.affected_keys == ['k|a', 'k|b']
assert result.retained_entries == []
print('step_04_smoke ok')
