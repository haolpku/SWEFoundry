#!/usr/bin/env python3
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mini_systemd_unit_linter as m

NL = chr(10)
root = pathlib.Path(tempfile.mkdtemp(prefix='unit-linter-smoke-3-'))
try:
    units_dir = root / 'units'
    units_dir.mkdir()
    (units_dir / 'target.target').write_text(NL.join(['[Unit]', 'Wants=app.service db.service', '']), encoding='utf-8')
    (units_dir / 'app.service').write_text(NL.join(['[Unit]', 'After=db.service', '']), encoding='utf-8')
    (units_dir / 'db.service').write_text(NL.join(['[Unit]', 'Description=Database', '']), encoding='utf-8')
    units = m.load_units([str(units_dir)])
    assert m.plan_activation(units, 'target.target') == ['db.service', 'app.service', 'target.target']
    cycle_dir = root / 'cycle'
    cycle_dir.mkdir()
    (cycle_dir / 'target.target').write_text(NL.join(['[Unit]', 'Wants=a.service b.service', '']), encoding='utf-8')
    (cycle_dir / 'a.service').write_text(NL.join(['[Unit]', 'After=b.service', '']), encoding='utf-8')
    (cycle_dir / 'b.service').write_text(NL.join(['[Unit]', 'After=a.service', '']), encoding='utf-8')
    try:
        m.plan_activation(m.load_units([str(cycle_dir)]), 'target.target')
    except m.DependencyCycleError as exc:
        assert 'a.service' in exc.cycle and 'b.service' in exc.cycle
    else:
        raise AssertionError('cycle must raise DependencyCycleError')
finally:
    shutil.rmtree(root)
