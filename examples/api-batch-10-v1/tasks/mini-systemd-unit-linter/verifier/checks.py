#!/usr/bin/env python3

_STEP_CHECKS = {
    'step-1': [
        ('canonical_unit_names_sorted', '''
import mini_systemd_unit_linter as m
root = write_units({'Zeta.SERVICE': NL.join(['[Unit]', 'Description=Z', '']), 'alpha.service': NL.join(['[Unit]', 'Description=A', ''])})
units = m.load_units([str(root)])
names = [unit.name for unit in units]
assert names == ['alpha.service', 'zeta.service'], names
return {'names': names}
'''),
        ('comment_handling_and_section_semantics', '''
import mini_systemd_unit_linter as m
root = write_units({'demo.service': NL.join(['# top comment', '[Unit] ; trailing section comment', 'Description = Demo # trailing value comment', 'Requires= OTHER.SERVICE ; dependency comment', '', '[Install]', 'WantedBy=multi-user.target', ''])})
unit = m.load_units([str(root)])[0]
assert unit.get('Unit', 'Description') == 'Demo', unit.sections
assert unit.values('Requires') == ('other.service',), unit.values('Requires')
assert unit.get('Install', 'WantedBy') == 'multi-user.target'
return {'requires': unit.values('Requires')}
'''),
        ('duplicate_scalar_key_rejected', '''
import mini_systemd_unit_linter as m
root = write_units({'bad.service': NL.join(['[Service]', 'ExecStart=/bin/true', 'ExecStart=/bin/false', ''])})
try:
    m.load_units([str(root)])
except ValueError as exc:
    assert 'duplicate key Service.ExecStart' in str(exc), str(exc)
    return {'raised': 'ValueError'}
raise AssertionError('duplicate scalar key was accepted')
'''),
        ('malformed_section_header_rejected', '''
import mini_systemd_unit_linter as m
root = write_units({'bad.service': NL.join(['[Unit', 'Description=Bad', ''])})
try:
    m.load_units([str(root)])
except ValueError as exc:
    assert 'malformed section header' in str(exc), str(exc)
    return {'raised': 'ValueError'}
raise AssertionError('malformed section header was accepted')
'''),
        ('duplicate_normalized_unit_name_rejected', '''
import mini_systemd_unit_linter as m
root_one = BASE / 'units-one'
root_two = BASE / 'units-two'
root_one.mkdir()
root_two.mkdir()
(root_one / 'A.service').write_text(NL.join(['[Unit]', 'Description=A', '']), encoding='utf-8')
(root_two / 'a.service').write_text(NL.join(['[Unit]', 'Description=a', '']), encoding='utf-8')
try:
    m.load_units([str(root_one), str(root_two)])
except ValueError as exc:
    assert 'duplicate unit name a.service' in str(exc), str(exc)
    return {'raised': 'ValueError'}
raise AssertionError('duplicate normalized names were accepted')
'''),
        ('file_path_input_supported', '''
import mini_systemd_unit_linter as m
root = write_units({'single.service': NL.join(['[Unit]', 'Description=Single', ''])})
units = m.load_units([str(root / 'single.service')])
assert [unit.name for unit in units] == ['single.service']
return {'count': len(units)}
'''),
        ('read_only_state_check', '''
import mini_systemd_unit_linter as m
root = write_units({'safe.service': NL.join(['[Unit]', 'Description=Safe', ''])})
before = snapshot(root)
units = m.load_units([str(root)])
after = snapshot(root)
assert before == after, {'before': before, 'after': after}
assert units[0].name == 'safe.service'
return {'files_unchanged': True}
'''),
    ],
    'step-2': [
        ('requires_missing_is_error', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'Requires=missing.service', ''])})
problems = m.validate_unit_graph(m.load_units([str(root)]))
assert [(p.severity, p.kind, p.dependency) for p in problems] == [('error', 'Requires', 'missing.service')], problems
return {'problem_count': len(problems)}
'''),
        ('wants_missing_is_warning', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'Wants=optional.service', ''])})
problems = m.validate_unit_graph(m.load_units([str(root)]))
assert [(p.severity, p.kind, p.dependency) for p in problems] == [('warning', 'Wants', 'optional.service')]
return {'severity': problems[0].severity}
'''),
        ('edge_type_severity_and_problem_ordering', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'After=missing-after.service', 'Before=missing-before.service', 'Conflicts=missing-conflict.service', 'Wants=missing-want.service', 'Requires=missing-req.service', ''])})
problems = m.validate_unit_graph(m.load_units([str(root)]))
observed = [(p.severity, p.kind, p.dependency) for p in problems]
expected = [('error', 'Conflicts', 'missing-conflict.service'), ('error', 'Requires', 'missing-req.service'), ('warning', 'After', 'missing-after.service'), ('warning', 'Before', 'missing-before.service'), ('warning', 'Wants', 'missing-want.service')]
assert observed == expected, observed
return {'ordered': observed}
'''),
        ('root_confinement_loaded_units_only', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'Requires=outside.service', ''])})
outside = BASE / 'outside'
outside.mkdir()
(outside / 'outside.service').write_text(NL.join(['[Unit]', 'Description=Outside', '']), encoding='utf-8')
problems = m.validate_unit_graph(m.load_units([str(root)]))
assert len(problems) == 1 and problems[0].dependency == 'outside.service', problems
assert problems[0].severity == 'error'
return {'ignored_outside_file': True}
'''),
        ('known_dependencies_are_silent', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'Requires=db.service', 'Wants=cache.service', 'After=db.service', 'Before=cache.service', '']), 'db.service': NL.join(['[Unit]', 'Description=DB', '']), 'cache.service': NL.join(['[Unit]', 'Description=Cache', ''])})
problems = m.validate_unit_graph(m.load_units([str(root)]))
assert problems == [], problems
return {'problem_count': 0}
'''),
        ('duplicate_parse_regression', '''
import mini_systemd_unit_linter as m
root = write_units({'bad.service': NL.join(['[Service]', 'ExecStart=/bin/true', 'ExecStart=/bin/false', ''])})
try:
    m.load_units([str(root)])
except ValueError:
    return {'duplicate_rejected': True}
raise AssertionError('step 1 duplicate regression')
'''),
        ('read_only_state_check', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'Requires=missing.service', ''])})
units = m.load_units([str(root)])
before = snapshot(root)
_ = m.validate_unit_graph(units)
after = snapshot(root)
assert before == after, {'before': before, 'after': after}
return {'files_unchanged': True}
'''),
    ],
    'step-3': [
        ('simple_after_order', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=app.service db.service', '']), 'app.service': NL.join(['[Unit]', 'After=db.service', '']), 'db.service': NL.join(['[Unit]', 'Description=DB', ''])})
plan = m.plan_activation(m.load_units([str(root)]), 'target.target')
assert plan == ['db.service', 'app.service', 'target.target'], plan
return {'plan': plan}
'''),
        ('before_order_is_honored', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=z-before.service a-after.service', '']), 'z-before.service': NL.join(['[Unit]', 'Before=a-after.service', '']), 'a-after.service': NL.join(['[Unit]', 'Description=After', ''])})
plan = m.plan_activation(m.load_units([str(root)]), 'target.target')
assert plan == ['z-before.service', 'a-after.service', 'target.target'], plan
return {'plan': plan}
'''),
        ('requires_closure_includes_requirements', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Requires=core.service', '']), 'core.service': NL.join(['[Unit]', 'Requires=leaf.service', '']), 'leaf.service': NL.join(['[Unit]', 'Description=Leaf', ''])})
plan = m.plan_activation(m.load_units([str(root)]), 'target.target')
assert plan == ['leaf.service', 'core.service', 'target.target'], plan
return {'plan': plan}
'''),
        ('wants_closure_includes_wants', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=optional.service', '']), 'optional.service': NL.join(['[Unit]', 'Description=Optional', '']), 'unrelated.service': NL.join(['[Unit]', 'Description=No', ''])})
plan = m.plan_activation(m.load_units([str(root)]), 'target.target')
assert plan == ['optional.service', 'target.target'], plan
return {'plan': plan}
'''),
        ('conflict_exclusion_raises', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=a.service b.service', '']), 'a.service': NL.join(['[Unit]', 'Conflicts=b.service', '']), 'b.service': NL.join(['[Unit]', 'Description=B', ''])})
try:
    m.plan_activation(m.load_units([str(root)]), 'target.target')
except ValueError as exc:
    assert 'conflict:' in str(exc), str(exc)
    return {'raised': 'ValueError'}
raise AssertionError('conflict was accepted')
'''),
        ('cycle_raises_with_sorted_witness', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=a.service b.service', '']), 'a.service': NL.join(['[Unit]', 'After=b.service', '']), 'b.service': NL.join(['[Unit]', 'After=a.service', ''])})
try:
    m.plan_activation(m.load_units([str(root)]), 'target.target')
except m.DependencyCycleError as exc:
    assert exc.cycle == tuple(sorted(exc.cycle)), exc.cycle
    assert exc.cycle == ('a.service', 'b.service', 'target.target'), exc.cycle
    return {'cycle': exc.cycle}
raise AssertionError('cycle was accepted')
'''),
        ('deterministic_lexical_order', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=b.service a.service', '']), 'b.service': NL.join(['[Unit]', 'Description=B', '']), 'a.service': NL.join(['[Unit]', 'Description=A', ''])})
plan = m.plan_activation(m.load_units([str(root)]), 'target.target')
assert plan == ['a.service', 'b.service', 'target.target'], plan
return {'plan': plan}
'''),
        ('read_only_state_check', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=app.service', '']), 'app.service': NL.join(['[Unit]', 'Description=App', ''])})
units = m.load_units([str(root)])
before = snapshot(root)
_ = m.plan_activation(units, 'target.target')
after = snapshot(root)
assert before == after, {'before': before, 'after': after}
return {'files_unchanged': True}
'''),
    ],
    'step-4': [
        ('required_failure_skips_dependent', '''
import mini_systemd_unit_linter as m
root = write_units({'db.service': NL.join(['[Unit]', 'Description=DB', '']), 'app.service': NL.join(['[Unit]', 'Requires=db.service', '']), 'target.target': NL.join(['[Unit]', 'Wants=app.service', ''])})
units = m.load_units([str(root)])
replay = m.replay_activation(units, ['db.service', 'app.service', 'target.target'], {'db.service'})
assert replay.failed == ('db.service',), replay
assert replay.skipped == ('app.service',), replay
assert 'target.target' in replay.started, replay
return {'replay': {'started': replay.started, 'skipped': replay.skipped, 'failed': replay.failed}}
'''),
        ('wanted_failure_continues', '''
import mini_systemd_unit_linter as m
root = write_units({'cache.service': NL.join(['[Unit]', 'Description=Cache', '']), 'app.service': NL.join(['[Unit]', 'Wants=cache.service', ''])})
units = m.load_units([str(root)])
replay = m.replay_activation(units, ['cache.service', 'app.service'], {'cache.service'})
assert replay.failed == ('cache.service',), replay
assert replay.skipped == (), replay
assert replay.started == ('app.service',), replay
return {'started': replay.started}
'''),
        ('restart_on_failure_with_burst_recovers', '''
import mini_systemd_unit_linter as m
root = write_units({'svc.service': NL.join(['[Unit]', 'Description=Svc', '[Service]', 'Restart=on-failure', 'StartLimitBurst=2', ''])})
replay = m.replay_activation(m.load_units([str(root)]), ['svc.service'], {'svc.service'})
assert replay.started == ('svc.service',), replay
assert replay.failed == (), replay
return {'started': replay.started}
'''),
        ('restart_limit_one_fails', '''
import mini_systemd_unit_linter as m
root = write_units({'svc.service': NL.join(['[Unit]', 'Description=Svc', '[Service]', 'Restart=always', 'StartLimitBurst=1', ''])})
replay = m.replay_activation(m.load_units([str(root)]), ['svc.service'], {'svc.service'})
assert replay.started == (), replay
assert replay.failed == ('svc.service',), replay
return {'failed': replay.failed}
'''),
        ('unknown_plan_entry_is_skipped', '''
import mini_systemd_unit_linter as m
root = write_units({'known.service': NL.join(['[Unit]', 'Description=Known', ''])})
replay = m.replay_activation(m.load_units([str(root)]), ['known.service', 'ghost.service'], set())
assert replay.started == ('known.service',), replay
assert replay.skipped == ('ghost.service',), replay
return {'skipped': replay.skipped}
'''),
        ('canonical_set_output_sorted', '''
import mini_systemd_unit_linter as m
root = write_units({'z.service': NL.join(['[Unit]', 'Description=Z', '']), 'a.service': NL.join(['[Unit]', 'Description=A', '']), 'm.service': NL.join(['[Unit]', 'Description=M', ''])})
replay = m.replay_activation(m.load_units([str(root)]), ['z.service', 'a.service', 'm.service'], {'z.service', 'a.service'})
assert replay.failed == ('a.service', 'z.service'), replay
assert replay.started == ('m.service',), replay
return {'failed': replay.failed, 'started': replay.started}
'''),
        ('required_skip_propagates_transitively', '''
import mini_systemd_unit_linter as m
root = write_units({'db.service': NL.join(['[Unit]', 'Description=DB', '']), 'mid.service': NL.join(['[Unit]', 'Requires=db.service', '']), 'app.service': NL.join(['[Unit]', 'Requires=mid.service', ''])})
replay = m.replay_activation(m.load_units([str(root)]), ['db.service', 'mid.service', 'app.service'], {'db.service'})
assert replay.failed == ('db.service',), replay
assert replay.skipped == ('app.service', 'mid.service'), replay
return {'skipped': replay.skipped}
'''),
        ('read_only_state_check', '''
import mini_systemd_unit_linter as m
root = write_units({'app.service': NL.join(['[Unit]', 'Description=App', ''])})
units = m.load_units([str(root)])
before = snapshot(root)
_ = m.replay_activation(units, ['app.service'], set())
after = snapshot(root)
assert before == after, {'before': before, 'after': after}
return {'files_unchanged': True}
'''),
    ],
    'step-5': [
        ('healthy_boot_audit_recovery_summary', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=app.service db.service', '']), 'app.service': NL.join(['[Unit]', 'After=db.service', 'Wants=cache.service', '']), 'db.service': NL.join(['[Unit]', 'Description=DB', '']), 'cache.service': NL.join(['[Unit]', 'Description=Cache', ''])})
report = m.audit_units([str(root)], 'target.target', {'cache.service'})
assert report.units == ('app.service', 'cache.service', 'db.service', 'target.target'), report.units
assert report.problems == (), report.problems
assert report.errors == (), report.errors
assert report.replay is not None
assert 'app.service' in report.replay.started and 'target.target' in report.replay.started, report.replay
assert 'failed:cache.service' in report.recovery, report.recovery
assert report.recovery == tuple(sorted(report.recovery)), report.recovery
return {'recovery': report.recovery}
'''),
        ('cycle_keeps_validation_problems', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=a.service b.service', '']), 'a.service': NL.join(['[Unit]', 'Requires=missing.service', 'After=b.service', '']), 'b.service': NL.join(['[Unit]', 'After=a.service', ''])})
report = m.audit_units([str(root)], 'target.target', set())
assert report.errors and 'dependency cycle:' in report.errors[0], report.errors
assert len(report.problems) == 1, report.problems
problem = report.problems[0]
assert (problem.severity, problem.kind, problem.dependency) == ('error', 'Requires', 'missing.service'), problem
assert report.plan == (), report.plan
assert report.replay is None
return {'errors': report.errors, 'problems': [(p.severity, p.kind, p.dependency) for p in report.problems]}
'''),
        ('duplicate_load_error_mapped', '''
import mini_systemd_unit_linter as m
root = write_units({'bad.service': NL.join(['[Service]', 'ExecStart=/bin/true', 'ExecStart=/bin/false', ''])})
report = m.audit_units([str(root)], 'bad.service', set())
assert report.units == (), report.units
assert report.problems == (), report.problems
assert report.plan == (), report.plan
assert report.replay is None
assert len(report.errors) == 1 and report.errors[0].startswith('load: '), report.errors
return {'error': report.errors[0]}
'''),
        ('requires_validation_regression', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=app.service', '']), 'app.service': NL.join(['[Unit]', 'Requires=missing.service', ''])})
report = m.audit_units([str(root)], 'target.target', set())
assert [(p.severity, p.kind, p.dependency) for p in report.problems] == [('error', 'Requires', 'missing.service')], report.problems
return {'problems': [(p.severity, p.kind, p.dependency) for p in report.problems]}
'''),
        ('before_planning_regression', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=z-before.service a-after.service', '']), 'z-before.service': NL.join(['[Unit]', 'Before=a-after.service', '']), 'a-after.service': NL.join(['[Unit]', 'Description=After', ''])})
report = m.audit_units([str(root)], 'target.target', set())
assert report.plan == ('z-before.service', 'a-after.service', 'target.target'), report.plan
return {'plan': report.plan}
'''),
        ('wanted_failure_replay_regression', '''
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=app.service', '']), 'app.service': NL.join(['[Unit]', 'Wants=cache.service', '']), 'cache.service': NL.join(['[Unit]', 'Description=Cache', ''])})
report = m.audit_units([str(root)], 'target.target', {'cache.service'})
assert report.replay is not None
assert 'cache.service' in report.replay.failed, report.replay
assert 'app.service' in report.replay.started, report.replay
assert 'target.target' in report.replay.started, report.replay
return {'replay': {'started': report.replay.started, 'failed': report.replay.failed}}
'''),
        ('deterministic_units_and_recovery_sorted', '''
import mini_systemd_unit_linter as m
root = write_units({'z.service': NL.join(['[Unit]', 'Description=Z', '']), 'a.service': NL.join(['[Unit]', 'Description=A', '']), 'target.target': NL.join(['[Unit]', 'Wants=z.service a.service', ''])})
report = m.audit_units([str(root)], 'target.target', {'z.service'})
assert report.units == ('a.service', 'target.target', 'z.service'), report.units
assert report.recovery == tuple(sorted(report.recovery)), report.recovery
assert 'failed:z.service' in report.recovery and 'started:a.service' in report.recovery, report.recovery
return {'units': report.units, 'recovery': report.recovery}
'''),
        ('read_only_state_check', '''
import dataclasses
import mini_systemd_unit_linter as m
root = write_units({'target.target': NL.join(['[Unit]', 'Wants=app.service', '']), 'app.service': NL.join(['[Unit]', 'Description=App', ''])})
before = snapshot(root)
report = m.audit_units([str(root)], 'target.target', set())
after = snapshot(root)
assert before == after, {'before': before, 'after': after}
assert isinstance(report.units, tuple) and isinstance(report.problems, tuple) and isinstance(report.plan, tuple) and isinstance(report.errors, tuple) and isinstance(report.recovery, tuple)
try:
    report.plan = ()
except dataclasses.FrozenInstanceError:
    pass
else:
    raise AssertionError('UnitAuditReport must be frozen/read-only')
return {'files_unchanged': True, 'frozen': True}
'''),
    ],
}


def get_checks(step_id):
    return list(_STEP_CHECKS[step_id])
