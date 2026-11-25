"""Exercise the pneumatic FMU offline, without Soft ESC, a master, or hardware."""
from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

import fmpy
from fmpy import extract, read_model_description
from fmpy.fmi2 import (FMU2Slave, defaultCallbacks, fmi2CallbackFunctions,
                      fmi2CallbackAllocateMemoryTYPE, fmi2CallbackFreeMemoryTYPE)
from fmpy.validation import validate_fmu

ROOT = Path(__file__).resolve().parents[2]
REAL_OUTPUTS = ['position', 'velocity', 'pressure_cap', 'pressure_rod', 'pneumatic_force']
BOOL_OUTPUTS = ['retracted_sensor', 'extended_sensor', 'valve_extended']


def runtime_callbacks():
    """Match the official OpenModelica 1.27.1 Windows UCRT build.

    Its CVODE teardown frees one callback-allocated structure with native free().
    FMPy's default Windows MSVCRT callbacks therefore cause a heap error on exit.
    Keep this local to the test importer; do not modify FMPy or the FMU globally.
    """
    if sys.platform != 'win32':
        return defaultCallbacks
    crt = ctypes.CDLL('ucrtbase.dll')
    callbacks = fmi2CallbackFunctions()
    callbacks.logger = defaultCallbacks.logger
    callbacks.allocateMemory = fmi2CallbackAllocateMemoryTYPE(('calloc', crt))
    callbacks.freeMemory = fmi2CallbackFreeMemoryTYPE(('free', crt))
    callbacks._crt = crt  # Retain the library for the lifetime of the callbacks.
    return callbacks


def commands(t: float) -> tuple[bool, bool]:
    # Boundaries are shared by the 1 ms and 8 ms communication grids.
    return (0.4 <= t < 0.52 or 2.0 <= t < 2.12,
            1.2 <= t < 1.32 or 2.8 <= t < 2.92)


def run_case(fmu_path: Path, output: Path, name: str, step: float,
             stroke: float = 0.1, pressure: float = 600000,
             max_fmu_step: float = .0001) -> tuple[dict, list[dict]]:
    md = read_model_description(str(fmu_path), validate=True)
    variables = {v.name: v for v in md.modelVariables}
    assert md.fmiVersion == '2.0' and md.coSimulation is not None
    for key in REAL_OUTPUTS + BOOL_OUTPUTS:
        assert variables[key].causality == 'output', key
    for key in ['extend_command', 'retract_command']:
        assert variables[key].causality == 'input', key
    real_refs = [variables[key].valueReference for key in REAL_OUTPUTS]
    bool_refs = [variables[key].valueReference for key in BOOL_OUTPUTS]
    input_refs = [variables[key].valueReference for key in ['extend_command', 'retract_command']]
    rows: list[dict] = []
    latencies: list[float] = []
    duration = 4.0
    substeps = max(1, math.ceil(step / max_fmu_step))
    fmu_step = step / substeps
    wall_start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='fmu-', dir=output) as temporary:
        # Confine automatically cleaned extraction directories to the test output.
        assert Path(temporary).resolve().is_relative_to(output.resolve())
        extract(str(fmu_path), unzipdir=temporary)
        slave = FMU2Slave(guid=md.guid, unzipDirectory=temporary,
                          modelIdentifier=md.coSimulation.modelIdentifier, instanceName=name)
        instantiated = False
        initialized = False
        try:
            slave.instantiate(callbacks=runtime_callbacks())
            instantiated = True
            slave.setupExperiment(tolerance=1e-6, startTime=0.0, stopTime=duration)
            slave.setReal([variables['stroke'].valueReference,
                           variables['supply_gauge_pressure'].valueReference], [stroke, pressure])
            slave.setBoolean(input_refs, [False, False])
            slave.enterInitializationMode()
            slave.exitInitializationMode()
            initialized = True

            def sample(t: float, inputs: tuple[bool, bool]) -> None:
                real_values = slave.getReal(real_refs)
                bool_values = slave.getBoolean(bool_refs)
                if not all(math.isfinite(value) for value in real_values):
                    raise AssertionError(f'{name}: nonfinite output at {t}')
                row = {'time_s': t, 'extend_command': inputs[0], 'retract_command': inputs[1]}
                row.update(zip(REAL_OUTPUTS, real_values))
                row.update((key, bool(value)) for key, value in zip(BOOL_OUTPUTS, bool_values))
                rows.append(row)

            sample(0.0, (False, False))
            for i in range(round(duration / step)):
                t = round(i * step, 9)
                inputs = commands(t)
                slave.setBoolean(input_refs, inputs)
                started = time.perf_counter_ns()
                try:
                    for substep in range(substeps):
                        slave.doStep(currentCommunicationPoint=round(t + substep*fmu_step, 12),
                                     communicationStepSize=fmu_step)
                except Exception as exc:
                    raise RuntimeError(f'{name}: doStep failed at t={t}; last output={rows[-1]}') from exc
                latencies.append((time.perf_counter_ns() - started) / 1e6)
                sample(round((i + 1) * step, 9), inputs)
        finally:
            if instantiated:
                try:
                    if initialized:
                        slave.terminate()
                finally:
                    slave.freeInstance()

    with (output / f'{name}.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert rows[0]['retracted_sensor'] and not rows[0]['extended_sensor'], 'Initial end sensors'
    assert abs(rows[0]['position']) < 1e-9, 'Initial position'
    assert not any(r['retracted_sensor'] and r['extended_sensor'] for r in rows), 'Overlapping sensors'
    assert all(r['pressure_cap'] > 0 and r['pressure_rod'] > 0 for r in rows), 'Absolute pressure'
    assert all(-0.002 <= r['position'] <= stroke + 0.002 for r in rows), 'Travel bounds'
    at = lambda t: rows[round(t / step)]
    if pressure:
        for t in [1.0, 2.6]:
            r = at(t)
            assert r['extended_sensor'] and not r['retracted_sensor'], f'{name}: extension at {t}'
            assert abs(r['position'] - stroke) < 0.001, f'{name}: extension position'
            assert r['valve_extended'], 'OFF/OFF must retain the extended valve direction'
            assert not r['extend_command'] and not r['retract_command'], 'Pulse must have ended'
        for t in [1.8, 3.6, 4.0]:
            r = at(t)
            assert r['retracted_sensor'] and not r['extended_sensor'], f'{name}: retraction at {t}'
            assert abs(r['position']) < 0.001, f'{name}: retraction position'
            assert not r['valve_extended'], 'OFF/OFF must retain the retracted valve direction'
        assert any(not r['retracted_sensor'] and not r['extended_sensor'] for r in rows), 'Mid-stroke'
    else:
        assert max(abs(r['position']) for r in rows) < 1e-6, 'No motion without air supply'
        assert not any(r['extended_sensor'] for r in rows), 'No extended sensor without motion'
    ordered = sorted(latencies)
    return {
        'case': name, 'passed': True, 'step_s': step, 'stroke_m': stroke,
        'fmu_do_step_s': fmu_step, 'fmu_calls_per_control_step': substeps,
        'supply_gauge_pressure_pa': pressure, 'simulated_seconds': duration,
        'wall_seconds': time.perf_counter() - wall_start,
        'position_min_m': min(r['position'] for r in rows),
        'position_max_m': max(r['position'] for r in rows),
        'control_step_calculation_ms': {'mean': statistics.mean(latencies),
                       'p95': ordered[math.ceil(0.95 * len(ordered)) - 1], 'max': max(latencies)},
    }, rows


def plot_trace(output: Path, rows: list[dict], reference: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return  # CSV and numerical validation do not depend on the plot package.
    t = [r['time_s'] for r in rows]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, layout='constrained')
    axes[0].plot([r['time_s'] for r in reference], [1000*r['position'] for r in reference],
                 color='#bac6d4', label='0.05 ms FMU reference', linewidth=3)
    axes[0].plot(t, [1000*r['position'] for r in rows], color='#185abc', label='8 ms control / 0.1 ms FMU steps')
    axes[0].set_ylabel('Position (mm)')
    axes[0].legend(loc='upper right', fontsize=8)
    axes[0].set_title('Windows FMI 2.0 Co-Simulation / CVODE — double-acting cylinder')
    for key, label, color in [('pressure_cap', 'Cap chamber', '#185abc'),
                              ('pressure_rod', 'Rod chamber', '#d97706')]:
        axes[1].plot(t, [(r[key]-101325)/1e5 for r in rows], label=label, color=color)
    axes[1].set_ylabel('Gauge pressure (bar)')
    axes[1].legend(fontsize=8)
    for offset, key in enumerate(['extend_command', 'retract_command', 'extended_sensor', 'retracted_sensor']):
        axes[2].step(t, [float(r[key])*.7 + offset for r in rows], where='post', label=key)
    axes[2].set_yticks([.35, 1.35, 2.35, 3.35], ['Extend input', 'Retract input', 'Extended', 'Retracted'])
    axes[2].set_xlabel('Simulation time (s)')
    for ax in axes:
        ax.grid(alpha=.2)
    fig.savefig(output / 'roundtrip.png', dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fmu', type=Path, default=ROOT / 'model_artifacts/SoftESCDoubleActingCylinder-win64.fmu')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/pneumatic-fmu-windows/results')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    issues = validate_fmu(str(args.fmu))
    if issues:
        raise RuntimeError('FMU validation failed:\n' + '\n'.join(issues))
    report = {'passed': False, 'platform': platform.platform(), 'python': platform.python_version(),
              'allocation_callbacks': 'Windows UCRT' if sys.platform == 'win32' else 'FMPy default',
              'fmpy': fmpy.__version__, 'cases': []}
    with args.fmu.open('rb') as stream:
        report['fmu_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    try:
        traces = {}
        for name, step, stroke, pressure, fmu_step in [
            ('roundtrip_8ms_substeps', .008, .1, 600000, .0001),
            ('roundtrip_reference', .001, .1, 600000, .00005),
            ('stroke_50mm', .008, .05, 600000, .0001),
            ('no_air', .008, .1, 0, .0001),
        ]:
            result, rows = run_case(args.fmu, args.output, name, step, stroke, pressure, fmu_step)
            report['cases'].append(result)
            traces[name] = rows
            print(json.dumps(result), flush=True)
        reference = traces['roundtrip_reference']
        errors = [abs(r['position']-reference[round(r['time_s']/.001)]['position'])
                  for r in traces['roundtrip_8ms_substeps']]
        report['fmu_step_comparison'] = {'max_position_difference_m': max(errors),
                                         'acceptance_m': .003,
                                         'reference_fmu_step_s': .00005, 'tested_fmu_step_s': .0001}
        assert max(errors) < .003, '0.05 ms / 0.1 ms FMU trajectory difference exceeds 3 mm'
        plot_trace(args.output, traces['roundtrip_8ms_substeps'], reference)
        report['passed'] = True
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: {args.output / "summary.json"}', flush=True)


if __name__ == '__main__':
    main()
