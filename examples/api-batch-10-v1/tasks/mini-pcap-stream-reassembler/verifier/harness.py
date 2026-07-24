from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys


def workspace_from_env() -> Path:
    return Path(os.environ.get('TDF_WORKSPACE', Path.cwd())).resolve()


def tests_dir_from_env(workspace: Path) -> Path:
    return Path(os.environ.get('TDF_TESTS_DIR', workspace / '.tdf-tests')).resolve()


def reward_dir_from_env(workspace: Path) -> Path:
    return Path(os.environ.get('TDF_REWARD_DIR', workspace / '.tdf-reward')).resolve()


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def case_prelude(workspace: Path) -> str:
    codebase = workspace / 'environment' / 'codebase'
    lines = [
        'import dataclasses',
        'import json',
        'import os',
        'import struct',
        'import sys',
        'sys.dont_write_bytecode = True',
        'sys.path.insert(0, ' + repr(str(codebase)) + ')',
        'from pcap_reassembler import PcapPacket, parse_pcap, TcpSegment, decode_tcp_segments, TcpStream, reassemble_tcp_streams, TcpTimeoutEvent, compute_tcp_timeouts, PcapAuditReport, audit_pcap_streams',
    ]
    return chr(10).join(lines) + chr(10)


def fixture_source() -> str:
    return r'''
def make_pcap(records, endian='<', snaplen=65535, network=1):
    magic = bytes.fromhex('d4c3b2a1') if endian == '<' else bytes.fromhex('a1b2c3d4')
    out = [magic + struct.pack(endian + 'HHIIII', 2, 4, 0, 0, snaplen, network)]
    for ts_sec, ts_usec, payload in records:
        out.append(struct.pack(endian + 'IIII', ts_sec, ts_usec, len(payload), len(payload)) + payload)
    return b''.join(out)

def eth_ipv4_tcp(seq=1000, ack=0, flags=0x18, payload=b'', src='10.0.0.1', dst='10.0.0.2', sport=1234, dport=80, ip_options=b'', tcp_options=b'', fragment=0):
    src_bytes = bytes(int(p) for p in src.split('.'))
    dst_bytes = bytes(int(p) for p in dst.split('.'))
    ihl = 20 + len(ip_options)
    if ihl % 4:
        raise AssertionError('ip options must be four-byte aligned')
    data_offset = 20 + len(tcp_options)
    if data_offset % 4:
        raise AssertionError('tcp options must be four-byte aligned')
    offset_flags = ((data_offset // 4) << 12) | flags
    tcp = struct.pack('!HHIIHHHH', sport, dport, seq, ack, offset_flags, 4096, 0, 0) + tcp_options + payload
    total = ihl + len(tcp)
    ip = bytes([(4 << 4) | (ihl // 4), 0]) + struct.pack('!H', total) + struct.pack('!H', 0) + struct.pack('!H', fragment) + bytes([64, 6]) + struct.pack('!H', 0) + src_bytes + dst_bytes + ip_options
    eth = b'\x02\x00\x00\x00\x00\x02' + b'\x02\x00\x00\x00\x00\x01' + struct.pack('!H', 0x0800)
    return eth + ip + tcp

def eth_ipv4_udp(payload=b'udp', src='10.0.0.1', dst='10.0.0.2'):
    src_bytes = bytes(int(p) for p in src.split('.'))
    dst_bytes = bytes(int(p) for p in dst.split('.'))
    udp = struct.pack('!HHHH', 1111, 2222, 8 + len(payload), 0) + payload
    total = 20 + len(udp)
    ip = bytes([0x45, 0]) + struct.pack('!H', total) + b'\x00\x00\x00\x00' + bytes([64, 17]) + b'\x00\x00' + src_bytes + dst_bytes
    eth = b'\x02\x00\x00\x00\x00\x02' + b'\x02\x00\x00\x00\x00\x01' + struct.pack('!H', 0x0800)
    return eth + ip + udp

def checkpoint_json(segments=None, packets=None):
    return json.dumps({'segments': segments or [], 'packets': packets or []}, sort_keys=True).encode('utf-8')
'''


def run_case(name: str, body: str, workspace: Path, tests_dir: Path) -> dict:
    cases_dir = tests_dir / 'isolated_cases'
    cases_dir.mkdir(parents=True, exist_ok=True)
    script = cases_dir / (name + '.py')
    source = case_prelude(workspace) + fixture_source() + chr(10) + body + chr(10) + "print('TDF_RESULT:' + json.dumps({'ok': True}, sort_keys=True))" + chr(10)
    script.write_text(source, encoding='utf-8')
    cmd = [sys.executable, '-I', '-B', str(script)]
    proc = subprocess.run(cmd, cwd=str(workspace), env=clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    ok = proc.returncode == 0 and any(line.startswith('TDF_RESULT:') for line in proc.stdout.splitlines())
    return {'name': name, 'passed': bool(ok), 'returncode': proc.returncode, 'stdout_tail': proc.stdout[-1200:], 'stderr_tail': proc.stderr[-1200:]}


def run_step(step_id: str, checks: list[tuple[str, str]]) -> int:
    workspace = workspace_from_env()
    tests_dir = tests_dir_from_env(workspace)
    reward_dir = reward_dir_from_env(workspace)
    tests_dir.mkdir(parents=True, exist_ok=True)
    reward_dir.mkdir(parents=True, exist_ok=True)
    results = [run_case(name, body, workspace, tests_dir) for name, body in checks]
    passed = sum(1 for r in results if r['passed'])
    correctness = 1.0 if passed == len(results) else passed / len(results)
    metrics = {
        'correctness': correctness,
        'code_quality': 1.0,
        'reasoning': 1.0,
        'efficiency': 1.0,
        'weighted_total': correctness,
        'release_pass': 1 if correctness == 1.0 else 0,
    }
    evidence = {'step_id': step_id, 'checks': results}
    ctrf_tests = [{'name': r['name'], 'status': 'passed' if r['passed'] else 'failed'} for r in results]
    ctrf = {'results': {'tool': {'name': 'tdf-black-box-verifier'}, 'summary': {'tests': len(results), 'passed': passed, 'failed': len(results) - passed}, 'tests': ctrf_tests}}
    (reward_dir / 'reward.txt').write_text(str(metrics['weighted_total']) + chr(10), encoding='utf-8')
    (reward_dir / 'reward.json').write_text(json.dumps(metrics, sort_keys=True, indent=2) + chr(10), encoding='utf-8')
    (reward_dir / 'evidence.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + chr(10), encoding='utf-8')
    (reward_dir / 'ctrf.json').write_text(json.dumps(ctrf, sort_keys=True, indent=2) + chr(10), encoding='utf-8')
    return 0 if metrics['release_pass'] == 1 else 1
