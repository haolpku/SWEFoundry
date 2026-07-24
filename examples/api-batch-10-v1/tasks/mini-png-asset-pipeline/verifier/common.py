from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

CASE_PREFIX = r'''
import json, os, struct, sys, zlib
sys.dont_write_bytecode = True
sys.path.insert(0, {codebase!r})
from png_asset_pipeline import *
SIG = b'\x89PNG\r\n\x1a\n'
def crc_value(typ, data=b''):
    return zlib.crc32(typ.encode('ascii') + data) & 0xffffffff
def make_chunk(typ, data=b'', crc=None):
    value = crc_value(typ, data) if crc is None else crc
    return struct.pack('>I', len(data)) + typ.encode('ascii') + data + struct.pack('>I', value)
def make_png(parts):
    return SIG + b''.join(parts)
def ihdr_data(width=1, height=1, bit_depth=8, color_type=2, compression=0, filter_method=0, interlace=0):
    return struct.pack('>IIBBBBB', width, height, bit_depth, color_type, compression, filter_method, interlace)
def valid_png(extra=(), color_type=2, compression=0, idat=b'abc'):
    return make_png([make_chunk('IHDR', ihdr_data(4, 3, 8, color_type, compression)), *extra, make_chunk('IDAT', idat), make_chunk('IEND')])
def assert_raises_valueerror(fn, contains=None):
    try:
        fn()
    except ValueError as exc:
        msg = str(exc)
        if contains is not None and contains not in msg:
            raise AssertionError(f'expected ValueError containing {contains!r}, got {msg!r}')
        return msg
    raise AssertionError('expected ValueError')
def has_problem(problems, code=None, chunk_type=None):
    return any((code is None or p.code == code) and (chunk_type is None or p.chunk_type == chunk_type) for p in problems)
def has_action(actions, action=None, chunk_type=None, reason=None):
    return any((action is None or a.action == action) and (chunk_type is None or a.chunk_type == chunk_type) and (reason is None or reason in a.reason) for a in actions)
def chunk_snapshot(chunks):
    return [(c.offset, c.length, c.type, c.data, c.crc) for c in chunks]
'''

CHECKS = {
    'step-1': [
        ('parse_minimal_png_in_file_order', r'''
payloads = [('IHDR', ihdr_data(3, 2)), ('tEXt', b'Author\x00Ada'), ('IDAT', b'abc'), ('IEND', b'')]
data = make_png([make_chunk(t, p) for t, p in payloads])
chunks = parse_png_chunks(data)
assert [c.type for c in chunks] == [t for t, p in payloads]
offset = 8
for c, (typ, payload) in zip(chunks, payloads):
    assert c.offset == offset
    assert c.length == len(payload)
    assert c.end_offset == offset + 12 + len(payload)
    assert c.type_bytes == typ.encode('ascii')
    offset = c.end_offset
assert offset == len(data)
'''),
        ('bad_signature_raises_valueerror', r'''
assert_raises_valueerror(lambda: parse_png_chunks(b'not a png'), 'signature')
'''),
        ('truncated_chunk_header_raises', r'''
assert_raises_valueerror(lambda: parse_png_chunks(SIG + b'\x00\x00'), 'truncated')
'''),
        ('declared_length_past_buffer_is_truncated', r'''
bad = SIG + struct.pack('>I', 10) + b'IEND' + b'x'
assert_raises_valueerror(lambda: parse_png_chunks(bad), 'truncated')
'''),
        ('missing_iend_raises', r'''
data = make_png([make_chunk('IHDR', ihdr_data())])
assert_raises_valueerror(lambda: parse_png_chunks(data), 'IEND')
'''),
        ('trailing_bytes_after_iend_raises', r'''
data = valid_png() + b'trailing'
assert_raises_valueerror(lambda: parse_png_chunks(data), 'trailing')
'''),
        ('non_letter_chunk_type_rejected', r'''
data = SIG + struct.pack('>I', 0) + b'12ab' + struct.pack('>I', crc_value('IEND')) + make_chunk('IEND')
assert_raises_valueerror(lambda: parse_png_chunks(data))
'''),
        ('read_only_state_check', r'''
data = bytearray(valid_png())
before = bytes(data)
chunks = parse_png_chunks(data)
assert bytes(data) == before
assert [c.type for c in chunks][-1] == 'IEND'
'''),
    ],
    'step-2': [
        ('ancillary_crc_mismatch_reported', r'''
data = make_png([make_chunk('IHDR', ihdr_data()), make_chunk('tEXt', b'Author\x00Ada', crc=0), make_chunk('IEND')])
problems = validate_png_chunks(parse_png_chunks(data))
assert has_problem(problems, 'CRC_MISMATCH', 'tEXt')
'''),
        ('critical_crc_mismatch_reported', r'''
data = make_png([make_chunk('IHDR', ihdr_data(), crc=0), make_chunk('IEND')])
problems = validate_png_chunks(parse_png_chunks(data))
assert has_problem(problems, 'CRC_MISMATCH', 'IHDR')
'''),
        ('idat_before_ihdr_reported', r'''
data = make_png([make_chunk('IDAT', b'abc'), make_chunk('IHDR', ihdr_data()), make_chunk('IEND')])
problems = validate_png_chunks(parse_png_chunks(data))
assert has_problem(problems, 'IDAT_BEFORE_IHDR', 'IDAT') or has_problem(problems, 'CHUNK_BEFORE_IHDR', 'IDAT')
assert has_problem(problems, 'IHDR_NOT_FIRST')
'''),
        ('singleton_chunk_violations_reported', r'''
ih = ihdr_data()
chunks = [
    PngChunk(8, 13, 'IHDR', ih, crc_value('IHDR', ih)),
    PngChunk(33, 13, 'IHDR', ih, crc_value('IHDR', ih)),
    PngChunk(58, 3, 'PLTE', b'abc', crc_value('PLTE', b'abc')),
    PngChunk(73, 3, 'PLTE', b'def', crc_value('PLTE', b'def')),
    PngChunk(88, 0, 'IDAT', b'', crc_value('IDAT')),
    PngChunk(100, 0, 'IEND', b'', crc_value('IEND')),
    PngChunk(112, 0, 'IEND', b'', crc_value('IEND')),
]
problems = validate_png_chunks(chunks)
assert has_problem(problems, 'DUPLICATE_IHDR', 'IHDR')
assert has_problem(problems, 'DUPLICATE_PLTE', 'PLTE')
assert has_problem(problems, 'DUPLICATE_IEND', 'IEND')
'''),
        ('plte_after_idat_reported', r'''
data = make_png([make_chunk('IHDR', ihdr_data()), make_chunk('IDAT', b'abc'), make_chunk('PLTE', b'abc'), make_chunk('IEND')])
problems = validate_png_chunks(parse_png_chunks(data))
assert has_problem(problems, 'PLTE_AFTER_IDAT', 'PLTE')
'''),
        ('nonconsecutive_idat_reported', r'''
data = make_png([make_chunk('IHDR', ihdr_data()), make_chunk('IDAT', b'a'), make_chunk('tEXt', b'K\x00V'), make_chunk('IDAT', b'b'), make_chunk('IEND')])
problems = validate_png_chunks(parse_png_chunks(data))
assert has_problem(problems, 'NONCONSECUTIVE_IDAT', 'IDAT')
'''),
        ('problems_sorted_by_offset_and_code', r'''
data = make_png([make_chunk('IDAT', b'a'), make_chunk('IHDR', ihdr_data(), crc=0), make_chunk('tEXt', b'K\x00V', crc=0), make_chunk('IEND')])
problems = validate_png_chunks(parse_png_chunks(data))
pairs = [(p.offset, p.code, p.chunk_type) for p in problems]
assert pairs == sorted(pairs)
'''),
        ('read_only_state_check', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('tEXt', b'K\x00V', crc=0)]))
before = chunk_snapshot(chunks)
validate_png_chunks(chunks)
assert chunk_snapshot(chunks) == before
'''),
    ],
    'step-3': [
        ('ihdr_dimensions_extracted', r'''
chunks = parse_png_chunks(valid_png(color_type=6))
meta = extract_png_metadata(chunks)
assert (meta.width, meta.height, meta.bit_depth, meta.color_type) == (4, 3, 8, 6)
'''),
        ('text_metadata_keys_are_canonical', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('tEXt', b'Beta\x00two'), make_chunk('tEXt', b'Gamma\x00three'), make_chunk('tEXt', b'Alpha\x00one')]))
meta = extract_png_metadata(chunks)
assert list(meta.text.keys()) == ['Alpha', 'Beta', 'Gamma']
'''),
        ('duplicate_text_uses_canonical_first_value', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('tEXt', b'Key\x00z-last'), make_chunk('tEXt', b'Key\x00a-first')]))
meta = extract_png_metadata(chunks)
assert meta.text == {'Key': 'a-first'}
'''),
        ('ztxt_invalid_compression_method_rejected', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('zTXt', b'Zip\x00\x01payload')]))
assert_raises_valueerror(lambda: extract_png_metadata(chunks), 'compression method')
'''),
        ('ztxt_payload_not_inflated_or_decoded', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('zTXt', b'Zip\x00\x00not-valid-deflate')]))
meta = extract_png_metadata(chunks)
assert meta.text['Zip'] == '<compressed>'
'''),
        ('itxt_invalid_compression_method_rejected', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('iTXt', b'Intl\x00\x01\x09en\x00Name\x00payload')]))
assert_raises_valueerror(lambda: extract_png_metadata(chunks), 'compression method')
'''),
        ('invalid_ihdr_compression_rejected', r'''
chunks = parse_png_chunks(valid_png(compression=1))
assert_raises_valueerror(lambda: extract_png_metadata(chunks), 'compression method')
'''),
        ('idat_bytes_are_ignored_by_metadata', r'''
chunks = parse_png_chunks(valid_png(idat=b'not a zlib stream at all'))
meta = extract_png_metadata(chunks)
assert meta.width == 4 and meta.height == 3
'''),
        ('read_only_state_check', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('tEXt', b'A\x00B')]))
before = chunk_snapshot(chunks)
extract_png_metadata(chunks)
assert chunk_snapshot(chunks) == before
'''),
    ],
    'step-4': [
        ('duplicate_text_removal_planned', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('tEXt', b'Author\x00Ada'), make_chunk('tEXt', b'Author\x00Lovelace')]))
actions = plan_png_cleanup(chunks)
assert has_action(actions, 'remove', 'tEXt', 'duplicate text metadata')
'''),
        ('clean_png_empty_plan', r'''
assert plan_png_cleanup(parse_png_chunks(valid_png())) == []
'''),
        ('corrupt_ancillary_crc_repair_planned', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('tEXt', b'Author\x00Ada', crc=0)]))
actions = plan_png_cleanup(chunks)
assert has_action(actions, 'repair_crc', 'tEXt', 'CRC mismatch')
assert any(any(d.startswith('expected=') for d in a.details) for a in actions if a.chunk_type == 'tEXt')
'''),
        ('corrupt_critical_chunk_not_removed', r'''
data = make_png([make_chunk('IHDR', ihdr_data(), crc=0), make_chunk('IEND')])
actions = plan_png_cleanup(parse_png_chunks(data))
assert has_action(actions, 'cannot_remove', 'IHDR', 'corrupt critical chunk')
assert not has_action(actions, 'remove', 'IHDR')
'''),
        ('unsafe_unknown_ancillary_removed', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('aaXA', b'x')]))
actions = plan_png_cleanup(chunks)
assert has_action(actions, 'remove', 'aaXA', 'unsafe unknown ancillary')
'''),
        ('grayscale_palette_removal_planned', r'''
data = valid_png(extra=[make_chunk('PLTE', b'abc')], color_type=0)
actions = plan_png_cleanup(parse_png_chunks(data))
assert has_action(actions, 'remove', 'PLTE', 'palette not allowed')
'''),
        ('bad_palette_length_normalized', r'''
data = valid_png(extra=[make_chunk('PLTE', b'ab')], color_type=3)
actions = plan_png_cleanup(parse_png_chunks(data))
assert has_action(actions, 'normalize_palette', 'PLTE', 'palette length')
'''),
        ('plan_is_idempotent_and_sorted', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('aaXA', b'x'), make_chunk('tEXt', b'K\x00V'), make_chunk('tEXt', b'K\x00W')]))
a1 = plan_png_cleanup(chunks)
a2 = plan_png_cleanup(chunks)
assert a1 == a2
assert a1 == sorted(set(a1))
'''),
        ('read_only_state_check', r'''
chunks = parse_png_chunks(valid_png(extra=[make_chunk('aaXA', b'x')]))
before = chunk_snapshot(chunks)
plan_png_cleanup(chunks)
assert chunk_snapshot(chunks) == before
'''),
    ],
    'step-5': [
        ('valid_audit_preserves_all_outputs', r'''
data = valid_png(extra=[make_chunk('tEXt', b'Title\x00Good')])
report = audit_png(data)
assert report.parse_error is None
assert [c.type for c in report.chunks] == ['IHDR', 'tEXt', 'IDAT', 'IEND']
assert report.problems == []
assert report.cleanup_actions == []
assert report.metadata.text == {'Title': 'Good'}
assert report.recovery_guidance == []
'''),
        ('corrupt_ancillary_integrates_crc_and_cleanup', r'''
data = valid_png(extra=[make_chunk('tEXt', b'Title\x00Bad', crc=0)])
report = audit_png(data)
assert report.metadata is not None
assert has_problem(report.problems, 'CRC_MISMATCH', 'tEXt')
assert has_action(report.cleanup_actions, 'repair_crc', 'tEXt', 'CRC mismatch')
assert any('read-only' in g for g in report.recovery_guidance)
'''),
        ('truncated_write_recovery_guidance', r'''
bad = SIG + struct.pack('>I', 10) + b'IEND' + b'x'
report = audit_png(bad)
assert report.chunks == []
assert report.metadata is None
assert report.parse_error is not None
assert has_problem(report.problems, 'PARSE_ERROR', '')
assert any('discard the incomplete candidate' in g for g in report.recovery_guidance)
assert any('os.replace' in g for g in report.recovery_guidance)
'''),
        ('metadata_error_becomes_problem_not_exception', r'''
report = audit_png(valid_png(compression=1))
assert report.metadata is None
assert has_problem(report.problems, 'METADATA_ERROR', 'IHDR')
'''),
        ('step1_regression_trailing_iend_rejected', r'''
report = audit_png(valid_png() + b'extra')
assert report.parse_error is not None
assert has_problem(report.problems, 'PARSE_ERROR', '')
'''),
        ('step2_regression_idat_before_ihdr_reported', r'''
data = make_png([make_chunk('IDAT', b'a'), make_chunk('IHDR', ihdr_data()), make_chunk('IEND')])
report = audit_png(data)
assert has_problem(report.problems, 'IDAT_BEFORE_IHDR', 'IDAT') or has_problem(report.problems, 'CHUNK_BEFORE_IHDR', 'IDAT')
'''),
        ('step3_regression_canonical_metadata_order', r'''
data = valid_png(extra=[make_chunk('tEXt', b'Zed\x00z'), make_chunk('tEXt', b'Alpha\x00a')])
report = audit_png(data)
assert list(report.metadata.text.keys()) == ['Alpha', 'Zed']
'''),
        ('step4_regression_critical_crc_cannot_remove', r'''
data = make_png([make_chunk('IHDR', ihdr_data(), crc=0), make_chunk('IEND')])
report = audit_png(data)
assert has_problem(report.problems, 'CRC_MISMATCH', 'IHDR')
assert has_action(report.cleanup_actions, 'cannot_remove', 'IHDR', 'corrupt critical')
assert not has_action(report.cleanup_actions, 'remove', 'IHDR')
'''),
        ('read_only_state_check', r'''
data = bytearray(valid_png(extra=[make_chunk('tEXt', b'A\x00B')]))
before = bytes(data)
report = audit_png(data)
assert bytes(data) == before
assert report.parse_error is None
'''),
    ],
}

def _clean_env():
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env

def _run_case(workspace, body):
    codebase = str((workspace / 'environment' / 'codebase').resolve())
    script = CASE_PREFIX.replace('{codebase!r}', repr(codebase)) + '\ntry:\n' + textwrap.indent(body, '    ') + "\n    print(json.dumps({'ok': True}, sort_keys=True))\nexcept BaseException as exc:\n    print(json.dumps({'ok': False, 'error_type': type(exc).__name__, 'message': str(exc)}, sort_keys=True))\n    raise\n"
    proc = subprocess.run([sys.executable, '-I', '-c', script], cwd=str(workspace), env=_clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    parsed = None
    for line in reversed(proc.stdout.splitlines()):
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if parsed is None:
        parsed = {'ok': False, 'error_type': 'NoJsonResult', 'message': 'candidate case produced no JSON result'}
    ok = proc.returncode == 0 and parsed.get('ok') is True
    return {'passed': bool(ok), 'returncode': proc.returncode, 'error_type': parsed.get('error_type'), 'message': parsed.get('message')}

def run_step_verifier(step_id, tests_dir):
    workspace = Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()
    reward_dir = Path(os.environ.get('TDF_REWARD_DIR', workspace / 'reward')).resolve()
    reward_dir.mkdir(parents=True, exist_ok=True)
    checks = CHECKS[step_id]
    results = []
    for name, body in checks:
        result = _run_case(workspace, body)
        result['name'] = name
        results.append(result)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    correctness = 1.0 if passed == total else round(passed / total, 6)
    auxiliary = 1.0 if correctness == 1.0 else 0.0
    weighted = round(0.85 * correctness + 0.05 * auxiliary + 0.05 * auxiliary + 0.05 * auxiliary, 6)
    metrics = {'correctness': correctness, 'code_quality': auxiliary, 'reasoning': auxiliary, 'efficiency': auxiliary, 'weighted_total': weighted, 'release_pass': 1 if correctness == 1.0 else 0}
    evidence = {'task_id': 'mini-png-asset-pipeline', 'step_id': step_id, 'checks': results, 'summary': {'passed': passed, 'total': total}}
    ctrf = {'results': {'tool': {'name': 'tdf-black-box-verifier'}, 'summary': {'tests': total, 'passed': passed, 'failed': total - passed}, 'tests': [{'name': r['name'], 'status': 'passed' if r['passed'] else 'failed'} for r in results]}}
    (reward_dir / 'reward.txt').write_text(str(metrics['weighted_total']) + '\n', encoding='utf-8')
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if metrics['release_pass'] == 1 else 1
