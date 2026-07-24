#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from verifier.common import finalize, get_context, run_case

workspace, tests_dir, reward_dir = get_context('step-1')
checks = []
checks.append(run_case('origin_relative_names_case_canonicalization', r'''
from dns_zone_auditor import parse_zone
text = '$TTL 600\nWWW IN A 192.0.2.10\nAlias IN CNAME WWW\n@ IN NS Ns1.Example.COM.\n'
records = parse_zone(text, 'Example.COM')
owners = [r.owner for r in records]
assert 'www.example.com.' in owners
assert 'alias.example.com.' in owners
assert 'Alias.Example.COM.' not in owners
cname = [r for r in records if r.type == 'CNAME'][0]
assert cname.data == ('www.example.com.',)
ns = [r for r in records if r.type == 'NS'][0]
assert ns.data == ('ns1.example.com.',)
''', workspace))
checks.append(run_case('default_ttl_and_owner_inheritance', r'''
from dns_zone_auditor import parse_zone
text = '$TTL 7200\nwww IN A 192.0.2.1\n  IN AAAA 2001:db8::1\nother 300 IN A 192.0.2.2\n'
records = parse_zone(text, 'example.com')
www = [r for r in records if r.owner == 'www.example.com.']
assert {r.type for r in www} == {'A', 'AAAA'}
assert all(r.ttl == 7200 for r in www)
assert [r for r in records if r.owner == 'other.example.com.'][0].ttl == 300
''', workspace))
checks.append(run_case('txt_with_spaces_and_comments', r'''
from dns_zone_auditor import parse_zone
text = '$TTL 60\ninfo IN TXT "hello world; kept" ; dropped comment\n'
records = parse_zone(text, 'example.com')
assert len(records) == 1
assert records[0].owner == 'info.example.com.'
assert records[0].type == 'TXT'
assert records[0].data == ('hello world; kept',)
''', workspace))
checks.append(run_case('soa_parentheses_numeric_and_names', r'''
from dns_zone_auditor import parse_zone
text = '$TTL 300\n@ IN SOA Ns.EXAMPLE.com. HostMaster.EXAMPLE.com. (\n 2024010101 7200 3600 1209600 300 )\n'
records = parse_zone(text, 'Example.COM')
soa = records[0]
assert soa.owner == 'example.com.'
assert soa.type == 'SOA'
assert soa.data == ('ns.example.com.', 'hostmaster.example.com.', '2024010101', '7200', '3600', '1209600', '300')
''', workspace))
checks.append(run_case('malformed_directives_raise_valueerror', r'''
from dns_zone_auditor import parse_zone
bad_inputs = ['$TTL 10 20\n', '$ORIGIN\n', 'IN A 192.0.2.1\n', 'www IN MX 10 mail\n', 'www IN A not-an-ip\n']
for text in bad_inputs:
    try:
        parse_zone(text, 'example.com')
    except ValueError:
        pass
    else:
        raise AssertionError('expected ValueError for ' + text)
''', workspace))
checks.append(run_case('canonical_sorted_records', r'''
from dns_zone_auditor import parse_zone
text = 'b IN A 192.0.2.2\na IN TXT z\na IN A 192.0.2.1\n'
records = parse_zone(text, 'example.com')
keys = [(r.owner, r.type, r.data, r.ttl) for r in records]
assert keys == sorted(keys)
assert [r.owner for r in records] == ['a.example.com.', 'a.example.com.', 'b.example.com.']
''', workspace))
checks.append(run_case('origin_directive_and_aaaa_normalization', r'''
from dns_zone_auditor import parse_zone
text = '$ORIGIN Sub.Example.COM.\nHost IN AAAA 2001:0db8:0000:0000:0000:0000:0000:0001\nabs.example.NET. IN A 192.0.2.9\n'
records = parse_zone(text, 'example.com')
assert records[1].owner == 'host.sub.example.com.'
assert records[1].data == ('2001:db8::1',)
assert records[0].owner == 'abs.example.net.'
''', workspace))
checks.append(run_case('read_only_state_no_input_change', r'''
from dns_zone_auditor import parse_zone
text = 'WWW IN A 192.0.2.10\n'
origin = 'Example.COM'
before = (text, origin)
parse_zone(text, origin)
assert (text, origin) == before
''', workspace))
raise SystemExit(0 if finalize('step-1', checks, reward_dir) else 1)
