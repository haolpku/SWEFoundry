#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_http_cache_engine import audit_http_cache, build_cache_key

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    req = {'method': 'GET', 'scheme': 'http', 'host': 'Example.COM', 'path': '/asset', 'query': 'b=2&a=1', 'headers': {'Accept-Language': 'en'}}
    resp = {'status': '200', 'Cache-Control': 'max-age=100', 'Vary': 'Accept-Language', 'Date': 'Thu, 01 Jan 1970 00:00:00 GMT', 'body': 'payload'}
    key = build_cache_key(req, resp)
    snap = root / 'snapshot.json'
    snap.write_text(json.dumps({'entries': [{'method': 'GET', 'scheme': 'HTTP', 'host': 'Example.COM', 'path': '/asset', 'query': 'b=2&a=1', 'vary': ['accept-language'], 'request_headers': {'Accept-Language': 'en'}, 'response_headers': {'Cache-Control': 'max-age=100', 'Vary': 'Accept-Language', 'Date': 'Thu, 01 Jan 1970 00:00:00 GMT'}, 'status': 200, 'body': 'payload', 'stored_at': 0}]}), encoding='utf-8')
    report = audit_http_cache(str(snap), [], 10)
    assert key in report.fresh_keys
    bad = root / 'truncated.json'
    bad.write_text('{', encoding='utf-8')
    recovered = audit_http_cache(str(bad), [{'method': 'POST', 'host': 'example.com', 'path': '/asset'}], 10)
    assert recovered.recovery_actions == ['snapshot-unreadable']
print('step_05_smoke ok')
