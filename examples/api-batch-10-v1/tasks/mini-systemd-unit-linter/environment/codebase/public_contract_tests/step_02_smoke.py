#!/usr/bin/env python3
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mini_systemd_unit_linter as m

NL = chr(10)
root = pathlib.Path(tempfile.mkdtemp(prefix='unit-linter-smoke-2-'))
try:
    units_dir = root / 'units'
    units_dir.mkdir()
    (units_dir / 'app.service').write_text(NL.join(['[Unit]', 'Requires=missing-required.service', 'Wants=missing-wanted.service', '']), encoding='utf-8')
    units = m.load_units([str(units_dir)])
    problems = m.validate_unit_graph(units)
    observed = {(p.kind, p.dependency): p.severity for p in problems}
    assert observed[('Requires', 'missing-required.service')] == 'error'
    assert observed[('Wants', 'missing-wanted.service')] == 'warning'
finally:
    shutil.rmtree(root)
