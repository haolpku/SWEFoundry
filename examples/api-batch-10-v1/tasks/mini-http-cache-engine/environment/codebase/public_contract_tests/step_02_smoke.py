#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_http_cache_engine import HttpCacheEntry, evaluate_http_freshness

entry = HttpCacheEntry(key='k', method='GET', scheme='http', host='example.com', path='/', query='', response_headers={'cache-control': 'max-age=60', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT'}, stored_at=0)
assert evaluate_http_freshness(entry, 30).status == 'fresh'
assert evaluate_http_freshness(entry, 90).status == 'stale'
precedence = HttpCacheEntry(key='p', method='GET', scheme='http', host='example.com', path='/', query='', response_headers={'cache-control': 'max-age=10', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT', 'expires': 'Fri, 02 Jan 1970 00:00:00 GMT'}, stored_at=0)
decision = evaluate_http_freshness(precedence, 20)
assert decision.status == 'stale'
assert decision.reason != 'expires'
print('step_02_smoke ok')
