#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import pathlib
_repo_root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_repo_root))
from verifier.common import finish

CHECKS = [
('host_case_normalized', r'''
from mini_http_cache_engine import build_cache_key
resp = {'status': '200', 'Cache-Control': 'max-age=60'}
a = build_cache_key({'method': 'get', 'scheme': 'HTTP', 'host': 'Example.COM', 'path': '/p', 'query': 'a=1'}, resp)
b = build_cache_key({'method': 'GET', 'scheme': 'http', 'host': 'example.com', 'path': '/p', 'query': 'a=1'}, resp)
print(json.dumps({'ok': a == b and a.startswith('v1|GET|http|example.com|/p|a=1'), 'details': {'a': a, 'b': b}}))
'''),
('query_order_canonical', r'''
from mini_http_cache_engine import build_cache_key
resp = {'status': '200', 'Cache-Control': 'max-age=60'}
a = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'query': 'b=2&a=1'}, resp)
b = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'query': 'a=1&b=2'}, resp)
print(json.dumps({'ok': a == b and '|a=1&b=2' in a, 'details': {'key': a}}))
'''),
('vary_header_in_key', r'''
from mini_http_cache_engine import build_cache_key
resp = {'status': '200', 'Cache-Control': 'max-age=60', 'Vary': 'Accept-Language'}
en = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'headers': {'Accept-Language': 'en'}}, resp)
fr = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'headers': {'Accept-Language': 'fr'}}, resp)
print(json.dumps({'ok': en != fr and 'vary:accept-language=en' in en and 'vary:accept-language=fr' in fr, 'details': {'en': en, 'fr': fr}}))
'''),
('method_normalization_head', r'''
from mini_http_cache_engine import build_cache_key
key = build_cache_key({'method': 'head', 'host': 'example.com', 'path': '/'}, {'status': '200', 'Cache-Control': 'max-age=1'})
print(json.dumps({'ok': key.startswith('v1|HEAD|'), 'details': {'key': key}}))
'''),
('unsafe_method_rejected', r'''
from mini_http_cache_engine import build_cache_key
try:
    build_cache_key({'method': 'POST', 'host': 'example.com', 'path': '/'}, {'status': '200', 'Cache-Control': 'max-age=1'})
    ok = False
except Exception:
    ok = True
print(json.dumps({'ok': ok, 'details': {}}))
'''),
('no_store_rejected', r'''
from mini_http_cache_engine import build_cache_key
try:
    build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/'}, {'status': '200', 'Cache-Control': 'no-store'})
    ok = False
except Exception:
    ok = True
print(json.dumps({'ok': ok, 'details': {}}))
'''),
('vary_star_rejected', r'''
from mini_http_cache_engine import build_cache_key
try:
    build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/'}, {'status': '200', 'Cache-Control': 'max-age=1', 'Vary': '*'})
    ok = False
except Exception:
    ok = True
print(json.dumps({'ok': ok, 'details': {}}))
'''),
('header_canonicalization_forms', r'''
from mini_http_cache_engine import build_cache_key
resp = {'status': '200', 'Cache-Control': 'max-age=1', 'Vary': 'Accept-Encoding'}
a = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/', 'headers': {'ACCEPT-ENCODING': 'gzip,   br'}}, resp)
b = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/', 'Header:Accept-Encoding': 'gzip, br'}, resp)
print(json.dumps({'ok': a == b and 'vary:accept-encoding=gzip, br' in a, 'details': {'a': a, 'b': b}}))
'''),
('read_only_inputs', r'''
from copy import deepcopy
from mini_http_cache_engine import build_cache_key
req = {'method': 'GET', 'host': 'Example.COM', 'path': '/p', 'headers': {'Accept-Language': 'en'}}
resp = {'status': '200', 'Cache-Control': 'max-age=1', 'Vary': 'Accept-Language'}
before = deepcopy((req, resp))
build_cache_key(req, resp)
print(json.dumps({'ok': before == (req, resp), 'details': {}}))
'''),
]

if __name__ == '__main__':
    raise SystemExit(finish('step-1', CHECKS, __file__))
