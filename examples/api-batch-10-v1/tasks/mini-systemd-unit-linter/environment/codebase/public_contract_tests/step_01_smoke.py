#!/usr/bin/env python3
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mini_systemd_unit_linter as m

NL = chr(10)
root = pathlib.Path(tempfile.mkdtemp(prefix='unit-linter-smoke-1-'))
try:
    units_dir = root / 'units'
    units_dir.mkdir()
    (units_dir / 'demo.service').write_text(NL.join(['# ignored comment', '[Unit]', 'Description=Demo # trailing comment', 'Requires=OTHER.service', '[Install]', 'WantedBy=multi-user.target', '']), encoding='utf-8')
    units = m.load_units([str(units_dir)])
    assert [unit.name for unit in units] == ['demo.service']
    assert units[0].get('Unit', 'Description') == 'Demo'
    assert units[0].values('Requires') == ('other.service',)
    duplicate_dir = root / 'dupe'
    duplicate_dir.mkdir()
    (duplicate_dir / 'bad.service').write_text(NL.join(['[Service]', 'ExecStart=/bin/true', 'ExecStart=/bin/false', '']), encoding='utf-8')
    try:
        m.load_units([str(duplicate_dir)])
    except ValueError:
        pass
    else:
        raise AssertionError('duplicate ExecStart must raise ValueError')
finally:
    shutil.rmtree(root)
