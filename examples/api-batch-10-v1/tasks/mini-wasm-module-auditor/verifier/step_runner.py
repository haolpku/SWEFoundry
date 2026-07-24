#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap
from dataclasses import dataclass

@dataclass(frozen=True)
class Check:
    name: str
    body: str

STEP_SLUGS = {
    1: '1-read-wasm-binary-sections',
    2: '2-decode-type-import-and-export-metadata',
    3: '3-validate-structural-integrity',
    4: '4-report-compatibility-migrations',
    5: '5-integrated-wasm-audit',
}

PRELUDE = r'''
import json
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, CODEBASE)

def leb(n):
    out = []
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

def nm(s):
    b = s.encode('utf-8')
    return leb(len(b)) + b

def sec(i, payload):
    return bytes([i]) + leb(len(payload)) + payload

def mod(*sections):
    return b'\x00asm\x01\x00\x00\x00' + b''.join(sections)

def custom(s, tail=b''):
    return sec(0, nm(s) + tail)

def finish(payload):
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0)

try:
    import wasm_auditor as wa
BODY
except Exception as exc:
    finish({'ok': False, 'exc_type': type(exc).__name__, 'message': str(exc)})
'''

def _script(codebase: pathlib.Path, body: str) -> str:
    return PRELUDE.replace('CODEBASE', repr(str(codebase))).replace('BODY', textwrap.indent(body, '    '))

def _run_case(workspace: pathlib.Path, check: Check) -> dict:
    codebase = workspace / 'environment' / 'codebase'
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    proc = subprocess.run([sys.executable, '-I', '-c', _script(codebase, check.body)], cwd=str(codebase), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return {'name': check.name, 'passed': False, 'message': 'candidate subprocess failed'}
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return {'name': check.name, 'passed': False, 'message': 'candidate produced no JSON'}
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {'name': check.name, 'passed': False, 'message': 'candidate produced invalid JSON'}
    return {'name': check.name, 'passed': bool(payload.get('ok') is True), 'message': str(payload.get('message', ''))[:160], 'details': payload.get('details')}

CASES = {
1: [
Check('empty_module_parses', "sections = wa.parse_wasm_sections(mod())\nassert sections == []\nfinish({'ok': True})"),
Check('bad_magic_raises', "try:\n    wa.parse_wasm_sections(b'bad!\\x01\\x00\\x00\\x00')\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('bad magic accepted')"),
Check('truncated_header_raises', "try:\n    wa.parse_wasm_sections(b'\\x00asm')\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('truncated header accepted')"),
Check('ordered_section_offsets_and_names', "data = mod(custom('abc'), sec(1, b'\\x00'))\nsections = wa.parse_wasm_sections(data)\nassert [(s.id, s.name, s.offset, s.size, s.payload) for s in sections] == [(0, 'custom', 8, 4, b'\\x03abc'), (1, 'type', 14, 1, b'\\x00')]\nfinish({'ok': True})"),
Check('truncated_section_payload_raises', "try:\n    wa.parse_wasm_sections(b'\\x00asm\\x01\\x00\\x00\\x00\\x01\\x05abc')\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('truncated payload accepted')"),
Check('truncated_leb_length_raises', "try:\n    wa.parse_wasm_sections(b'\\x00asm\\x01\\x00\\x00\\x00\\x01\\x80')\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('truncated leb accepted')"),
Check('leb_u32_overflow_raises', "try:\n    wa.parse_wasm_sections(b'\\x00asm\\x01\\x00\\x00\\x00\\x01\\x80\\x80\\x80\\x80\\x80\\x00')\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('overflow leb accepted')"),
Check('read_only_state_check', "buf = bytearray(mod(sec(1, b'abc')))\nsections = wa.parse_wasm_sections(buf)\nbuf[-1] = 90\nassert sections[0].payload == b'abc'\nblocked = False\ntry:\n    sections[0].payload = b'zzz'\nexcept Exception:\n    blocked = True\nassert blocked\nfinish({'ok': True})"),
],
2: [
Check('exported_function_summary', "sections = wa.parse_wasm_sections(mod(sec(3, b'\\x01\\x00'), sec(7, b'\\x01' + nm('run') + b'\\x00\\x00')))\ns = wa.summarize_wasm_symbols(sections)\nassert [(x.kind, x.name, x.index) for x in s] == [('function', 'function[0]', 0), ('export-function', 'run', 0)]\nfinish({'ok': True})"),
Check('invalid_utf8_import_name_raises', "bad = b'\\x01\\x01\\xff' + nm('f') + b'\\x00\\x00'\ntry:\n    wa.summarize_wasm_symbols(wa.parse_wasm_sections(mod(sec(2, bad))))\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('invalid utf8 accepted')"),
Check('separate_index_spaces_for_imports', "imp = b'\\x02' + nm('env') + nm('f') + b'\\x00\\x00' + nm('env') + nm('mem') + b'\\x02\\x00\\x01'\nexp = b'\\x02' + nm('f') + b'\\x00\\x00' + nm('mem') + b'\\x02\\x00'\ns = wa.summarize_wasm_symbols(wa.parse_wasm_sections(mod(sec(2, imp), sec(7, exp))))\nassert ('memory', 'env.mem', 0) in [(x.kind, x.name, x.index) for x in s]\nassert ('export-memory', 'mem', 0) in [(x.kind, x.name, x.index) for x in s]\nfinish({'ok': True})"),
Check('defined_function_index_after_import', "imp = b'\\x01' + nm('env') + nm('f') + b'\\x00\\x00'\ns = wa.summarize_wasm_symbols(wa.parse_wasm_sections(mod(sec(2, imp), sec(3, b'\\x01\\x00'))))\nassert ('function', 'function[1]', 1) in [(x.kind, x.name, x.index) for x in s]\nfinish({'ok': True})"),
Check('deterministic_symbol_order', "imp = b'\\x01' + nm('env') + nm('f') + b'\\x00\\x00'\nexp = b'\\x01' + nm('run') + b'\\x00\\x01'\ns = wa.summarize_wasm_symbols(wa.parse_wasm_sections(mod(sec(2, imp), sec(3, b'\\x01\\x00'), sec(7, exp))))\nassert [(x.kind, x.name, x.index) for x in s] == [('function', 'env.f', 0), ('function', 'function[1]', 1), ('export-function', 'run', 1)]\nfinish({'ok': True})"),
Check('export_memory_kind_descriptor', "memsec = b'\\x01\\x00\\x01'\nexp = b'\\x01' + nm('memory') + b'\\x02\\x00'\ns = wa.summarize_wasm_symbols(wa.parse_wasm_sections(mod(sec(5, memsec), sec(7, exp))))\nassert any(x.kind == 'export-memory' and x.descriptor == 'export memory index=0' for x in s)\nfinish({'ok': True})"),
Check('trailing_export_bytes_raise', "try:\n    wa.summarize_wasm_symbols(wa.parse_wasm_sections(mod(sec(7, b'\\x00\\x99'))))\nexcept ValueError:\n    finish({'ok': True})\nraise AssertionError('trailing export bytes accepted')"),
Check('read_only_state_check', "sections = wa.parse_wasm_sections(mod(sec(7, b'\\x00')))\nbefore = [s.payload for s in sections]\nwa.summarize_wasm_symbols(sections)\nassert [s.payload for s in sections] == before\nfinish({'ok': True})"),
],
3: [
Check('duplicate_type_section_reported', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(1, b'\\x00'), sec(1, b'\\x00'))))\nassert any(x.code == 'duplicate-section' and x.section_id == 1 for x in p)\nfinish({'ok': True})"),
Check('export_index_out_of_bounds_reported', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(7, b'\\x01' + nm('run') + b'\\x00\\x00'))))\nassert any(x.code == 'export-index' for x in p)\nfinish({'ok': True})"),
Check('custom_sections_do_not_break_order', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(1, b'\\x00'), custom('meta'), sec(2, b'\\x00'))))\nassert not any(x.code == 'section-order' for x in p)\nfinish({'ok': True})"),
Check('core_out_of_order_reported', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(3, b'\\x00'), sec(2, b'\\x00'))))\nassert any(x.code == 'section-order' for x in p)\nfinish({'ok': True})"),
Check('function_code_count_mismatch_reported', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(3, b'\\x01\\x00'), sec(10, b'\\x00'))))\nassert any(x.code == 'function-code-count' for x in p)\nfinish({'ok': True})"),
Check('deterministic_problem_sorting', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(3, b'\\x01\\x00'), sec(2, b'\\x00'), sec(2, b'\\x00'), sec(10, b'\\x00'))))\nkeys = [(x.offset, x.code, x.message, x.section_id) for x in p]\nassert keys == sorted(keys)\nfinish({'ok': True})"),
Check('malformed_import_reported_not_raised', "p = wa.validate_wasm_structure(wa.parse_wasm_sections(mod(sec(2, b'\\x01'))))\nassert any(x.code == 'malformed-section' for x in p)\nfinish({'ok': True})"),
Check('read_only_state_check', "sections = wa.parse_wasm_sections(mod(sec(3, b'\\x01\\x00'), sec(10, b'\\x00')))\nbefore = [s.payload for s in sections]\nwa.validate_wasm_structure(sections)\nassert [s.payload for s in sections] == before\nfinish({'ok': True})"),
],
4: [
Check('unknown_custom_section_advice', "a = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(custom('x-private'))))\nassert any(x.category == 'unknown-custom-section' and x.target == 'x-private' for x in a)\nfinish({'ok': True})"),
Check('canonical_name_section_advice', "a = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(custom('zzz'), custom('name'))))\nassert any(x.category == 'canonical-name-section' for x in a)\nfinish({'ok': True})"),
Check('unsupported_start_feature_advice', "a = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(sec(8, b'\\x00'))))\nassert any(x.category == 'unsupported-feature' and x.target == 'start' for x in a)\nfinish({'ok': True})"),
Check('deprecated_export_name_advice', "exp = b'\\x01' + nm('old__run') + b'\\x00\\x00'\na = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(sec(7, exp))))\nassert any(x.category == 'deprecated-name' and x.target == 'old__run' for x in a)\nfinish({'ok': True})"),
Check('deduplicates_equivalent_advice', "a = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(sec(8, b'\\x00'), sec(8, b'\\x01'))))\nassert sum(1 for x in a if x.category == 'unsupported-feature' and x.target == 'start') == 1\nfinish({'ok': True})"),
Check('stable_advice_ordering', "exp = b'\\x01' + nm('old__run') + b'\\x00\\x00'\na = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(custom('zzz'), custom('name'), sec(8, b'\\x00'), sec(7, exp))))\nkeys = [(x.category, x.target, x.message) for x in a]\nassert keys == sorted(keys)\nfinish({'ok': True})"),
Check('malformed_custom_recovery_advice', "a = wa.plan_wasm_migration(wa.parse_wasm_sections(mod(sec(0, b'\\x02a'))))\nassert any(x.category == 'malformed-custom' for x in a)\nfinish({'ok': True})"),
Check('read_only_state_check', "sections = wa.parse_wasm_sections(mod(custom('x-private'), sec(8, b'\\x00')))\nbefore = [s.payload for s in sections]\nwa.plan_wasm_migration(sections)\nassert [s.payload for s in sections] == before\nfinish({'ok': True})"),
],
5: [
Check('valid_module_audit', "data = mod(sec(3, b'\\x01\\x00'), sec(7, b'\\x01' + nm('run') + b'\\x00\\x00'), sec(10, b'\\x01\\x02\\x00\\x0b'))\nr = wa.audit_wasm(data)\nassert r.problems == ()\nassert any(s.kind == 'export-function' and s.name == 'run' for s in r.symbols)\nfinish({'ok': True})"),
Check('malformed_parse_recovered_as_problem', "r = wa.audit_wasm(b'\\x00asm\\x01\\x00\\x00\\x00\\x01\\x05abc')\nassert r.sections == () and r.symbols == () and r.advice == ()\nassert len(r.problems) == 1 and r.problems[0].code == 'parse-error'\nfinish({'ok': True})"),
Check('invalid_structure_suppresses_symbols', "r = wa.audit_wasm(mod(sec(7, b'\\x01' + nm('run') + b'\\x00\\x00')))\nassert any(p.code == 'export-index' for p in r.problems)\nassert r.symbols == ()\nfinish({'ok': True})"),
Check('malformed_export_recovery_no_crash', "r = wa.audit_wasm(mod(sec(7, b'\\x01' + nm('bad'))))\nassert any(p.code == 'malformed-section' for p in r.problems)\nassert r.symbols == ()\nfinish({'ok': True})"),
Check('report_and_sections_are_read_only', "r = wa.audit_wasm(mod(custom('x-private')))\nassert isinstance(r.sections, tuple) and isinstance(r.symbols, tuple) and isinstance(r.problems, tuple) and isinstance(r.advice, tuple)\nblocked = False\ntry:\n    r.sections = ()\nexcept Exception:\n    blocked = True\nassert blocked\nfinish({'ok': True})"),
Check('preserves_migration_advice', "r = wa.audit_wasm(mod(custom('x-private'), sec(8, b'\\x00')))\nassert any(a.category == 'unknown-custom-section' for a in r.advice)\nassert any(a.category == 'unsupported-feature' and a.target == 'start' for a in r.advice)\nfinish({'ok': True})"),
Check('regresses_step2_index_spaces', "imp = b'\\x02' + nm('env') + nm('f') + b'\\x00\\x00' + nm('env') + nm('mem') + b'\\x02\\x00\\x01'\nexp = b'\\x02' + nm('f') + b'\\x00\\x00' + nm('mem') + b'\\x02\\x00'\nr = wa.audit_wasm(mod(sec(2, imp), sec(7, exp)))\nassert not r.problems\nassert ('memory', 'env.mem', 0) in [(s.kind, s.name, s.index) for s in r.symbols]\nfinish({'ok': True})"),
Check('regresses_step3_custom_order', "r = wa.audit_wasm(mod(sec(1, b'\\x00'), custom('meta'), sec(2, b'\\x00')))\nassert not any(p.code == 'section-order' for p in r.problems)\nfinish({'ok': True})"),
Check('deterministic_repeat_audit', "data = mod(custom('x-private'), sec(8, b'\\x00'))\nr1 = wa.audit_wasm(data)\nr2 = wa.audit_wasm(data)\nassert repr(r1) == repr(r2)\nfinish({'ok': True})"),
],
}

CHECKS = {'step-1': [('empty_module_parses', 'delegated'), ('bad_magic_raises', 'delegated'), ('truncated_header_raises', 'delegated'), ('ordered_section_offsets_and_names', 'delegated'), ('truncated_section_payload_raises', 'delegated'), ('truncated_leb_length_raises', 'delegated'), ('leb_u32_overflow_raises', 'delegated'), ('read_only_state_check', 'delegated')], 'step-2': [('exported_function_summary', 'delegated'), ('invalid_utf8_import_name_raises', 'delegated'), ('separate_index_spaces_for_imports', 'delegated'), ('defined_function_index_after_import', 'delegated'), ('deterministic_symbol_order', 'delegated'), ('export_memory_kind_descriptor', 'delegated'), ('trailing_export_bytes_raise', 'delegated'), ('read_only_state_check', 'delegated')], 'step-3': [('duplicate_type_section_reported', 'delegated'), ('export_index_out_of_bounds_reported', 'delegated'), ('custom_sections_do_not_break_order', 'delegated'), ('core_out_of_order_reported', 'delegated'), ('function_code_count_mismatch_reported', 'delegated'), ('deterministic_problem_sorting', 'delegated'), ('malformed_import_reported_not_raised', 'delegated'), ('read_only_state_check', 'delegated')], 'step-4': [('unknown_custom_section_advice', 'delegated'), ('canonical_name_section_advice', 'delegated'), ('unsupported_start_feature_advice', 'delegated'), ('deprecated_export_name_advice', 'delegated'), ('deduplicates_equivalent_advice', 'delegated'), ('stable_advice_ordering', 'delegated'), ('malformed_custom_recovery_advice', 'delegated'), ('read_only_state_check', 'delegated')], 'step-5': [('valid_module_audit', 'delegated'), ('malformed_parse_recovered_as_problem', 'delegated'), ('invalid_structure_suppresses_symbols', 'delegated'), ('malformed_export_recovery_no_crash', 'delegated'), ('report_and_sections_are_read_only', 'delegated'), ('preserves_migration_advice', 'delegated'), ('regresses_step2_index_spaces', 'delegated'), ('regresses_step3_custom_order', 'delegated'), ('deterministic_repeat_audit', 'delegated')]}

def _write_outputs(reward_dir: pathlib.Path, step: int, results: list[dict]) -> int:
    reward_dir.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    correctness = 1.0 if passed == total else passed / total
    release_pass = 1 if correctness == 1.0 else 0
    metrics = {
        'correctness': correctness,
        'code_quality': 1.0 if release_pass else 0.0,
        'reasoning': 1.0 if release_pass else 0.0,
        'efficiency': 1.0 if release_pass else 0.0,
        'weighted_total': correctness,
        'release_pass': release_pass,
    }
    (reward_dir / 'reward.txt').write_text(str(metrics['weighted_total']) + '\n', encoding='utf-8')
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    evidence = {'step': step, 'checks': sorted(results, key=lambda r: r['name'])}
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    ctrf = {'results': {'tool': {'name': 'mini-wasm-module-auditor-blackbox-verifier'}, 'summary': {'tests': total, 'passed': passed, 'failed': total - passed}, 'tests': [{'name': r['name'], 'status': 'passed' if r['passed'] else 'failed', 'message': r.get('message', '')} for r in sorted(results, key=lambda x: x['name'])]}}
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 0 if release_pass else 1

def main(step: int) -> int:
    sys.dont_write_bytecode = True
    workspace = pathlib.Path(os.environ.get('TDF_WORKSPACE', pathlib.Path.cwd())).resolve()
    pathlib.Path(os.environ.get('TDF_TESTS_DIR', '.')).resolve()
    reward_dir = pathlib.Path(os.environ.get('TDF_REWARD_DIR', workspace / 'reward')).resolve()
    checks = CASES[step]
    results = [_run_case(workspace, c) for c in checks]
    return _write_outputs(reward_dir, step, results)
