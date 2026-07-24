#!/usr/bin/env python3
import pathlib
import sys

CODEBASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEBASE))

from mini_http_cache_engine import build_cache_key

response = {'status': '200', 'Cache-Control': 'max-age=60'}
key_a = build_cache_key({'method': 'get', 'scheme': 'HTTP', 'host': 'Example.COM', 'path': '/p', 'query': 'b=2&a=1'}, response)
key_b = build_cache_key({'method': 'GET', 'scheme': 'http', 'host': 'example.com', 'path': '/p', 'query': 'a=1&b=2'}, response)
assert key_a == key_b
assert key_a.startswith('v1|GET|http|example.com|/p|a=1&b=2')

vary_response = {'status': '200', 'Cache-Control': 'max-age=60', 'Vary': 'Accept-Language'}
en = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'headers': {'Accept-Language': 'en'}}, vary_response)
fr = build_cache_key({'method': 'GET', 'host': 'example.com', 'path': '/p', 'headers': {'Accept-Language': 'fr'}}, vary_response)
assert en != fr
assert 'vary:accept-language=en' in en
print('step_01_smoke ok')
