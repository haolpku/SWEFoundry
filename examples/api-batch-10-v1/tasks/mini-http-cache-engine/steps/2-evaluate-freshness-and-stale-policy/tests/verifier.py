#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import pathlib
_repo_root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_repo_root))
from verifier.common import finish

BASE = "from mini_http_cache_engine import HttpCacheEntry, evaluate_http_freshness\ndef entry(headers, status=200, stored_at=0):\n    return HttpCacheEntry(key='k', method='GET', scheme='http', host='example.com', path='/', query='', response_headers=headers, status=status, stored_at=stored_at)\n"
CHECKS = [
('max_age_fresh', BASE + r'''
d = evaluate_http_freshness(entry({'cache-control': 'max-age=60', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT'}), 30)
print(json.dumps({'ok': d.status == 'fresh' and d.age == 30 and d.freshness_lifetime == 60, 'details': d.__dict__}))
'''),
('expired_response_stale', BASE + r'''
d = evaluate_http_freshness(entry({'cache-control': 'max-age=10', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT'}), 20)
print(json.dumps({'ok': d.status == 'stale' and d.can_use_stale_if_error is False, 'details': d.__dict__}))
'''),
('cache_control_over_expires', BASE + r'''
d = evaluate_http_freshness(entry({'cache-control': 'max-age=10', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT', 'expires': 'Fri, 02 Jan 1970 00:00:00 GMT'}), 20)
print(json.dumps({'ok': d.status == 'stale' and d.reason != 'expires' and d.freshness_lifetime == 10, 'details': d.__dict__}))
'''),
('injected_clock_only', BASE + r'''
e = entry({'cache-control': 'max-age=10'})
a = evaluate_http_freshness(e, 5)
b = evaluate_http_freshness(e, 50)
print(json.dumps({'ok': a.status == 'fresh' and b.status == 'stale', 'details': {'early': a.__dict__, 'late': b.__dict__}}))
'''),
('age_header_precedence', BASE + r'''
d = evaluate_http_freshness(entry({'cache-control': 'max-age=60', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT', 'age': '70'}), 10)
print(json.dumps({'ok': d.status == 'stale' and d.age == 70, 'details': d.__dict__}))
'''),
('stale_if_error_window', BASE + r'''
d = evaluate_http_freshness(entry({'cache-control': 'max-age=10, stale-if-error=50', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT'}), 30)
print(json.dumps({'ok': d.status == 'stale' and d.can_use_stale_if_error is True and d.reason == 'stale-if-error', 'details': d.__dict__}))
'''),
('unusable_policy_and_status', BASE + r'''
a = evaluate_http_freshness(entry({'cache-control': 'no-store'}, status=200), 0)
b = evaluate_http_freshness(entry({'cache-control': 'max-age=10'}, status=500), 0)
print(json.dumps({'ok': a.status == 'unusable' and b.status == 'unusable', 'details': {'a': a.__dict__, 'b': b.__dict__}}))
'''),
('validators_reported', BASE + r'''
d = evaluate_http_freshness(entry({'cache-control': 'max-age=1', 'etag': '"abc"', 'last-modified': 'Thu, 01 Jan 1970 00:00:00 GMT'}), 0)
print(json.dumps({'ok': d.validators == ('"abc"', 'Thu, 01 Jan 1970 00:00:00 GMT'), 'details': {'validators': list(d.validators)}}))
'''),
('read_only_entry', BASE + r'''
e = entry({'cache-control': 'max-age=10'}, stored_at=0)
before = e.__dict__.copy()
evaluate_http_freshness(e, 5)
print(json.dumps({'ok': before == e.__dict__, 'details': {}}))
'''),
]

if __name__ == '__main__':
    raise SystemExit(finish('step-2', CHECKS, __file__))
