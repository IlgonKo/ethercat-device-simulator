# F-KR CMMT native FMUs

RF-022 ports the RF-015 kinematic drive to a common C++17 core (`drive.hpp`).
`fmi.cpp` exposes FMI 3.0 Co-Simulation. The artifacts contain a native Linux
x86-64 shared library and C++ sources, without a Python interpreter.

Build in the standard Docker builder with `bash scripts/docker/build.sh`, or
with the locked FMPy environment and g++ using
`python scripts/models/build-f-kr-cmmt-fmus.py`.
The script compiles core fault tests, validates FMI metadata, creates deterministic
archives and writes source/artifact SHA-256 provenance alongside each artifact.

- `FKrCmmtLinear-linux.fmu`: position m, velocity m/s, acceleration m/s2.
- `FKrCmmtRotary-linux.fmu`: rad, rad/s, rad/s2; accumulated position, no modulo.
- FMI variable names/types are identical. `modelDescription.xml` lists all inputs
  and outputs. Time is seconds. All inputs are sampled for each doStep.
- Step interval must be finite and in (0, 0.1] s. No event mode, early return,
  state serialization or Model Exchange is advertised.
- Instantiate/initialize starts disabled, at position/velocity zero, unreferenced.
  Mode requests are applied at standstill; accepted PP settings are latched.
- Disable cancels motion, preserves position/completed reference, requires new
  Enable and a fresh motion command. Controlword reset does not recreate FMU.
- Unexpected FMI execution failure requires a fresh instance. Soft ESC currently
  performs this through manual container restart.

The FMU has no EtherCAT OD, mapping, file storage, logging/management API or
external fault injection input. The adapter handles raw-unit conversion and OD
command/readback effects. The core-only test can inject drive Fault internally;
this is not a public FMU variable. CMMT vendor-complete behavior, motor electrical
physics, torque/load simulation and realtime guarantees are outside this model.

Compare with frozen Python using
`PYTHONPATH=src:. python -m unittest tests.integration.test_f_kr_fmu -v`.
Discrete status/mode must match each tick; numeric feedback and target readback
must remain within one raw OD LSB, both before and after encoding.
