#!/usr/bin/env python3
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mini_systemd_unit_linter as m

NL = chr(10)
root = pathlib.Path(tempfile.mkdtemp(prefix='unit-linter-smoke-5-'))
try:
    units_dir = root / 'units'
    units_dir.mkdir()
    (units_dir / 'target.target').write_text(NL.join(['[Unit]', 'Wants=app.service cache.service', '']), encoding='utf-8')
    (units_dir / 'app.service').write_text(NL.join(['[Unit]', 'After=cache.service', '']), encoding='utf-8')
    (units_dir / 'cache.service').write_text(NL.join(['[Unit]', 'Description=Cache', '']), encoding='utf-8')
    report = m.audit_units([str(units_dir)], 'target.target', {'cache.service'})
    assert report.units == ('app.service', 'cache.service', 'target.target')
    assert report.problems == ()
    assert report.replay is not None
    assert 'app.service' in report.replay.started
    assert 'failed:cache.service' in report.recovery
    cycle_dir = root / 'cycle'
    cycle_dir.mkdir()
    (cycle_dir / 'target.target').write_text(NL.join(['[Unit]', 'Wants=a.service b.service', '']), encoding='utf-8')
    (cycle_dir / 'a.service').write_text(NL.join(['[Unit]', 'Requires=missing.service', 'After=b.service', '']), encoding='utf-8')
    (cycle_dir / 'b.service').write_text(NL.join(['[Unit]', 'After=a.service', '']), encoding='utf-8')
    cycle_report = m.audit_units([str(cycle_dir)], 'target.target', set())
    assert cycle_report.errors
    assert cycle_report.problems and cycle_report.problems[0].dependency == 'missing.service'
finally:
    shutil.rmtree(root)
