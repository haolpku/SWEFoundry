#!/usr/bin/env python3
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mini_systemd_unit_linter as m

NL = chr(10)
root = pathlib.Path(tempfile.mkdtemp(prefix='unit-linter-smoke-4-'))
try:
    units_dir = root / 'units'
    units_dir.mkdir()
    (units_dir / 'db.service').write_text(NL.join(['[Unit]', 'Description=DB', '']), encoding='utf-8')
    (units_dir / 'app.service').write_text(NL.join(['[Unit]', 'Requires=db.service', 'Wants=cache.service', '']), encoding='utf-8')
    (units_dir / 'cache.service').write_text(NL.join(['[Unit]', 'Description=Cache', '']), encoding='utf-8')
    units = m.load_units([str(units_dir)])
    replay = m.replay_activation(units, ['cache.service', 'db.service', 'app.service'], {'cache.service'})
    assert 'cache.service' in replay.failed
    assert 'app.service' in replay.started
    replay = m.replay_activation(units, ['db.service', 'app.service'], {'db.service'})
    assert replay.failed == ('db.service',)
    assert replay.skipped == ('app.service',)
finally:
    shutil.rmtree(root)
