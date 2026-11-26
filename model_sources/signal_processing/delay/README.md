# SoftESCAnalogDelay

Native FMI 3.0 Co-Simulation, Linux x86-64. Independent raw Int16 transport delay.

- Input `command`: Int16; output `feedback`: Int16, initially zero.
- Fixed initialization parameter `delay_seconds`: Float64 seconds, default 0.016, range 0..10.
- At communication time t, sample the current input; after doStep(t,h), publish the latest sample satisfying sample_time + delay <= t+h.
- At h=8ms, a t=0 sample first appears at 8/16/24ms for delays 0/16/20ms.
- No interpolation, scaling, clamp, wall-clock progression, events, state serialization or late-response recovery.
- History and time are private per FMU instance. No doStep means no model-time advancement. Reset/re-instantiation clears history and feedback.
- Built from C because this is an integer discrete history buffer without a physical solver. It uses the same FMI boundary as the Modelica-exported cylinder; no Python delay substitute is used.

Build: `build/fmi-venv/bin/python scripts/models/build-analog-delay-fmu.py`.
The Docker builder compiles the library; no compiler is installed in the runtime image. FMI headers come from pinned FMPy and are included with their original license notices in the source FMU. Unimplemented capabilities return FMI Error; they do not report success.
