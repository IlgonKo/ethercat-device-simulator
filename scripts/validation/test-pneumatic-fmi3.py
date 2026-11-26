"""Offline validation of the Playground cylinder FMU; no Soft ESC or hardware."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile

import fmpy
from fmpy import extract, read_model_description, simulate_fmu
from fmpy.fmi3 import FMU3Slave
from fmpy.validation import validate_fmu
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ['position', 'velocity', 'pressure_cap', 'pressure_rod', 'pneumatic_force',
           'retracted_sensor', 'extended_sensor', 'valve_extended']
CASES = {
    'roundtrip_8ms': {'interval': .008, 'stroke': .1, 'pressure': 600000},
    'roundtrip_1ms': {'interval': .001, 'stroke': .1, 'pressure': 600000},
    'stroke_50mm': {'interval': .008, 'stroke': .05, 'pressure': 600000},
    'no_air': {'interval': .008, 'stroke': .1, 'pressure': 0},
    'event_mode_8ms': {'interval': .008, 'stroke': .1, 'pressure': 600000,
                      'event_mode': True, 'early_return': True},
}


def signals():
    # Duplicate timestamps explicitly describe the Boolean input discontinuities.
    rows = [(0., False, False)]
    old = (False, False)
    for t, new in [(0.4, (True, False)), (.52, (False, False)),
                   (1.2, (False, True)), (1.32, (False, False)),
                   (2., (True, False)), (2.12, (False, False)),
                   (2.8, (False, True)), (2.92, (False, False))]:
        rows.extend([(t, *old), (t, *new)])
        old = new
    rows.append((4., False, False))
    return np.array(rows, dtype=[('time', np.float64), ('extend_command', np.bool_),
                                 ('retract_command', np.bool_)])


def check_results(result, stroke, pressure):
    assert abs(float(result['time'][-1]) - 4.) < 1e-9, 'Simulation did not reach 4 s'
    for name in OUTPUTS[:5]:
        assert np.isfinite(result[name]).all(), f'Nonfinite {name}'
    assert abs(float(result['position'][0])) < 1e-9, 'Initial position'
    assert result['retracted_sensor'][0] and not result['extended_sensor'][0], 'Initial sensors'
    assert not np.any(result['extended_sensor'] & result['retracted_sensor']), 'Overlapping sensors'
    assert np.all(result['pressure_cap'] > 0) and np.all(result['pressure_rod'] > 0), 'Absolute pressures'
    assert np.min(result['position']) >= -.002, 'Retraction endstop penetration exceeds 2 mm'
    assert np.max(result['position']) <= stroke + .002, 'Extension endstop penetration exceeds 2 mm'
    at = lambda t: result[np.argmin(np.abs(result['time'] - t))]
    if pressure:
        for t in (1., 2.6):
            r = at(t)
            assert r['extended_sensor'] and not r['retracted_sensor'], f'Extension sensor at {t}'
            assert abs(r['position'] - stroke) < .001, f'Extension position at {t}'
            assert r['valve_extended'], 'Valve must retain extension after input OFF'
        for t in (1.8, 3.6, 4.):
            r = at(t)
            assert r['retracted_sensor'] and not r['extended_sensor'], f'Retraction sensor at {t}'
            assert abs(r['position']) < .001, f'Retraction position at {t}'
            assert not r['valve_extended'], 'Valve must retain retraction after input OFF'
        assert np.any(~result['extended_sensor'] & ~result['retracted_sensor']), 'Midstroke sensors'
    else:
        assert np.max(np.abs(result['position'])) < 1e-6, 'Motion without supply air'
        assert not np.any(result['extended_sensor']), 'Extended sensor without supply air'


def run_with_event_mode(fmu_path, output, case):
    """Set discrete inputs only in initialization/event mode, per FMI 3.0."""
    md = read_model_description(str(fmu_path))
    vr = {v.name: v.valueReference for v in md.modelVariables}
    records = []
    stats = {'event_iterations': 0, 'early_returns': 0, 'do_step_calls': 0}
    next_event = math.inf
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='event-mode-', dir=output) as directory:
        extract(str(fmu_path), unzipdir=directory)
        fmu = FMU3Slave(guid=md.guid, unzipDirectory=directory,
                        modelIdentifier=md.coSimulation.modelIdentifier,
                        instanceName='pneumatic_event_test')
        instantiated = initialized = False
        try:
            fmu.instantiate(eventModeUsed=True, earlyReturnAllowed=True)
            instantiated = True
            fmu.setFloat64([vr['stroke'], vr['supply_gauge_pressure']],
                           [case['stroke'], case['pressure']])
            fmu.enterInitializationMode(tolerance=1e-6, startTime=0., stopTime=4.)
            fmu.setBoolean([vr['extend_command'], vr['retract_command']], [False, False])
            fmu.exitInitializationMode()
            initialized = True

            def update():
                nonlocal next_event
                for _ in range(100):
                    again, terminate, _, _, defined, when = fmu.updateDiscreteStates()
                    stats['event_iterations'] += 1
                    assert not terminate, 'FMU requested termination in event mode'
                    next_event = when if defined else math.inf
                    if not again:
                        fmu.enterStepMode()
                        return
                raise RuntimeError('Event iteration did not converge')

            def sample(t):
                records.append((t, *fmu.getFloat64([vr[n] for n in OUTPUTS[:5]]),
                                *fmu.getBoolean([vr[n] for n in OUTPUTS[5:]])))

            update()
            sample(0.)
            old = (False, False)
            step = case['interval']
            for i in range(round(4. / step)):
                t = round(i * step, 12)
                end = round((i + 1) * step, 12)
                new = (.4 <= t < .52 or 2. <= t < 2.12,
                       1.2 <= t < 1.32 or 2.8 <= t < 2.92)
                if new != old:
                    fmu.enterEventMode()
                    fmu.setBoolean([vr['extend_command'], vr['retract_command']], new)
                    update()
                    old = new
                for _ in range(10000):
                    if t >= end - 1e-12:
                        break
                    assert time.monotonic() - started < 60., 'Event simulation timeout'
                    if next_event <= t + 1e-12:
                        fmu.enterEventMode()
                        update()
                        continue
                    target = min(end, next_event)
                    event, terminate, early, last = fmu.doStep(
                        currentCommunicationPoint=t, communicationStepSize=target-t)
                    stats['do_step_calls'] += 1
                    stats['early_returns'] += int(early)
                    assert not terminate, 'FMU requested termination in doStep'
                    new_t = last if early else target
                    assert t - 1e-12 <= new_t <= target + 1e-12, 'Invalid lastSuccessfulTime'
                    assert new_t > t or event, 'No progress without an event'
                    t = new_t
                    if event or next_event <= t + 1e-12:
                        fmu.enterEventMode()
                        update()
                else:
                    raise RuntimeError('Too many events within one communication interval')
                sample(end)
        finally:
            if instantiated:
                try:
                    if initialized:
                        fmu.terminate()
                finally:
                    fmu.freeInstance()
    dtype = [('time', np.float64)] + [(n, np.float64) for n in OUTPUTS[:5]] + [(n, np.bool_) for n in OUTPUTS[5:]]
    return np.array(records, dtype=dtype), stats


def run_case(fmu, output, name):
    case = CASES[name]
    report = {'case': name, 'event_mode': False, 'early_return': False, **case, 'passed': False}
    started = time.perf_counter()
    try:
        if case.get('event_mode'):
            result, stats = run_with_event_mode(fmu, output, case)
            report.update(stats)
        else:
            result = simulate_fmu(
                str(fmu), fmi_type='CoSimulation', start_time=0., stop_time=4.,
                relative_tolerance=1e-6, output_interval=case['interval'],
                start_values={'stroke': case['stroke'], 'supply_gauge_pressure': case['pressure']},
                input=signals(), output=OUTPUTS, use_event_mode=False,
                early_return_allowed=False, timeout=60., validate=True)
        np.save(output / f'{name}.npy', result)
        np.savetxt(output / f'{name}.csv',
                   np.column_stack([result[key] for key in result.dtype.names]),
                   delimiter=',', header=','.join(result.dtype.names), comments='')
        check_results(result, case['stroke'], case['pressure'])
        report.update(passed=True, samples=len(result), simulated_seconds=float(result['time'][-1]),
                      position_min_m=float(np.min(result['position'])),
                      position_max_m=float(np.max(result['position'])),
                      final_position_m=float(result['position'][-1]),
                      lifecycle='instantiate / initialize / simulate / terminate / free completed')
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        traceback.print_exc()
    report['wall_seconds'] = time.perf_counter() - started
    (output / f'{name}.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    return report['passed']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fmu', type=Path, default=ROOT / 'model_artifacts/SoftESCDoubleActingCylinder-fmi3-web.fmu')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/pneumatic-cylinder/fmi3' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    parser.add_argument('--case', choices=list(CASES))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.case:
        return 0 if run_case(args.fmu.resolve(), args.output.resolve(), args.case) else 1
    report = {'passed': False, 'platform': platform.platform(), 'python': platform.python_version(),
              'fmpy': fmpy.__version__, 'fmu_sha256': hashlib.sha256(args.fmu.read_bytes()).hexdigest(),
              'validation_issues': validate_fmu(str(args.fmu)), 'cases': []}
    md = read_model_description(str(args.fmu), validate=True)
    assert md.fmiVersion == '3.0' and md.coSimulation is not None
    variables = {v.name: v for v in md.modelVariables}
    assert all(variables[n].causality == 'output' for n in OUTPUTS)
    assert all(variables[n].causality == 'input' and variables[n].type == 'Boolean'
               for n in ['extend_command', 'retract_command'])
    with zipfile.ZipFile(args.fmu) as z:
        report['binaries'] = [n for n in z.namelist() if n.startswith('binaries/')]
    report['generator'] = md.generationTool
    report['model_name'] = md.modelName
    assert not report['validation_issues'], report['validation_issues']
    for name in CASES:
        # Never mistake a previous successful child result for a crashed new run.
        p = args.output / f'{name}.json'
        p.unlink(missing_ok=True)
        command = [sys.executable, str(Path(__file__).resolve()), '--fmu', str(args.fmu.resolve()),
                   '--output', str(args.output.resolve()), '--case', name]
        try:
            child = subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=90)
            (args.output / f'{name}.log').write_text(child.stdout + child.stderr, encoding='utf-8')
            item = json.loads(p.read_text()) if p.exists() else {'case': name, 'passed': False}
            item['process_exit_code'] = child.returncode
            item['passed'] = item['passed'] and child.returncode == 0
        except subprocess.TimeoutExpired as exc:
            item = {'case': name, 'passed': False, 'error': 'Process timeout (90 s)'}
            (args.output / f'{name}.log').write_bytes((exc.stdout or b'') + (exc.stderr or b''))
        report['cases'].append(item)
        print(json.dumps(item), flush=True)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if all(item['passed'] for item in report['cases'][:2]):
        a = np.load(args.output / 'roundtrip_8ms.npy')
        b = np.load(args.output / 'roundtrip_1ms.npy')
        difference = np.abs(a['position'] - np.interp(a['time'], b['time'], b['position']))
        report['step_comparison'] = {'max_position_difference_m': float(difference.max()), 'acceptance_m': .003}
    report['passed'] = all(item['passed'] for item in report['cases']) and report.get('step_comparison', {}).get('max_position_difference_m', math.inf) < .003
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
