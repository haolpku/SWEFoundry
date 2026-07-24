#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import pathlib
_repo_root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_repo_root))
from verifier.common import finish

SNAP_BASE = "import json, tempfile, pathlib\nfrom mini_http_cache_engine import audit_http_cache, build_cache_key, HttpCacheEntry, evaluate_http_freshness, merge_http_304, invalidate_http_cache\ndef record(path='/asset', lang='en', body='payload'):\n    return {'method': 'GET', 'scheme': 'HTTP', 'host': 'Example.COM', 'path': path, 'query': 'b=2&a=1', 'vary': ['accept-language'], 'request_headers': {'Accept-Language': lang}, 'response_headers': {'Cache-Control': 'max-age=100', 'Vary': 'Accept-Language', 'Date': 'Thu, 01 Jan 1970 00:00:00 GMT', 'ETag': '\"' + lang + '\"'}, 'status': 200, 'body': body, 'stored_at': 0}\n"
CHECKS = [
('fresh_cache_audit', SNAP_BASE + r'''
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'snapshot.json'
    rec = record()
    p.write_text(json.dumps({'entries': [rec]}), encoding='utf-8')
    key = build_cache_key({'method': 'GET', 'scheme': 'http', 'host': 'example.com', 'path': '/asset', 'query': 'a=1&b=2', 'headers': {'Accept-Language': 'en'}}, {'status': '200', 'Cache-Control': 'max-age=100', 'Vary': 'Accept-Language', 'Date': 'Thu, 01 Jan 1970 00:00:00 GMT'})
    report = audit_http_cache(str(p), [], 10)
    ok = key in report.fresh_keys and report.stale_keys == [] and report.recovery_actions == ['snapshot-valid']
    print(json.dumps({'ok': ok, 'details': {'fresh': report.fresh_keys, 'actions': report.recovery_actions}}))
'''),
('truncated_snapshot_recovery', SNAP_BASE + r'''
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'bad.json'
    p.write_text('{', encoding='utf-8')
    report = audit_http_cache(str(p), [{'method': 'POST', 'host': 'example.com', 'path': '/asset'}], 10)
    print(json.dumps({'ok': report.recovered_entries == [] and report.invalidated_keys == [] and report.recovery_actions == ['snapshot-unreadable'], 'details': {'actions': report.recovery_actions, 'invalidated': report.invalidated_keys}}))
'''),
('snapshot_migration_canonical_metadata', SNAP_BASE + r'''
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'snapshot.json'
    p.write_text(json.dumps({'entries': [record()]}), encoding='utf-8')
    report = audit_http_cache(str(p), [], 10)
    e = report.recovered_entries[0]
    ok = e.scheme == 'http' and e.host == 'example.com' and e.query == 'a=1&b=2' and 'vary:accept-language=en' in e.key
    print(json.dumps({'ok': ok, 'details': e.to_snapshot_record()}))
'''),
('duplicate_snapshot_record_recovery', SNAP_BASE + r'''
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'snapshot.json'
    r = record()
    p.write_text(json.dumps({'entries': [r, r]}), encoding='utf-8')
    report = audit_http_cache(str(p), [], 10)
    ok = len(report.recovered_entries) == 1 and report.recovery_actions == ['record-1-ignored-duplicate-key']
    print(json.dumps({'ok': ok, 'details': {'actions': report.recovery_actions, 'count': len(report.recovered_entries)}}))
'''),
('regression_step1_vary_key', SNAP_BASE + r'''
resp = {'status': '200', 'Cache-Control': 'max-age=60', 'Vary': 'Accept-Language'}
en = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'headers': {'Accept-Language': 'en'}}, resp)
fr = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'headers': {'Accept-Language': 'fr'}}, resp)
print(json.dumps({'ok': en != fr and 'vary:accept-language=en' in en, 'details': {'en': en, 'fr': fr}}))
'''),
('regression_step2_max_age_precedence', SNAP_BASE + r'''
e = HttpCacheEntry(key='k', method='GET', scheme='http', host='example.com', path='/', query='', response_headers={'cache-control': 'max-age=10', 'date': 'Thu, 01 Jan 1970 00:00:00 GMT', 'expires': 'Fri, 02 Jan 1970 00:00:00 GMT'}, stored_at=0)
d = evaluate_http_freshness(e, 20)
print(json.dumps({'ok': d.status == 'stale' and d.freshness_lifetime == 10, 'details': d.__dict__}))
'''),
('regression_step3_merge_preserves_body', SNAP_BASE + r'''
e = HttpCacheEntry(key='k', method='GET', scheme='http', host='example.com', path='/', query='', response_headers={'etag': '"abc"'}, body='payload')
m = merge_http_304(e, {'status': '304', 'ETag': '"abc"', 'body': ''})
print(json.dumps({'ok': m.body == 'payload', 'details': {'body': m.body}}))
'''),
('regression_step4_invalidate_variants', SNAP_BASE + r'''
a = HttpCacheEntry(key='a', method='GET', scheme='http', host='example.com', path='/asset', query='', response_headers={'cache-control': 'max-age=1'})
b = HttpCacheEntry(key='b', method='GET', scheme='http', host='example.com', path='/asset', query='', response_headers={'cache-control': 'max-age=1'})
r = invalidate_http_cache([b, a], {'method': 'POST', 'scheme': 'http', 'host': 'example.com', 'path': '/asset'})
print(json.dumps({'ok': r.affected_keys == ['a', 'b'], 'details': {'affected': r.affected_keys}}))
'''),
('read_only_snapshot_and_events', SNAP_BASE + r'''
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'snapshot.json'
    payload = json.dumps({'entries': [record()]})
    p.write_text(payload, encoding='utf-8')
    events = [{'method': 'GET', 'host': 'example.com', 'path': '/asset'}]
    before_events = json.loads(json.dumps(events))
    audit_http_cache(str(p), events, 10)
    print(json.dumps({'ok': p.read_text(encoding='utf-8') == payload and events == before_events, 'details': {}}))
'''),
]

if __name__ == '__main__':
    raise SystemExit(finish('step-5', CHECKS, __file__))
