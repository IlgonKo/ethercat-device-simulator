# Soft ESC

**Connect behaviour models to a real EtherCAT bus as virtual drives and remote I/O.**

Soft ESC turns FMUs and other supported behaviour models into virtual EtherCAT
slaves. An EtherCAT master can configure and operate these devices through SDO
and PDO communication, alongside physical equipment on the same bus.

The package runs independently of Motion Server, DT Demo, ROS 2 and Omniverse.
Motion Server and its Axis/I/O Control Panels are the validated integration
clients; device pairing, application sequences and DT visualization belong to
the applications using Soft ESC.

## What you can do

- **Simulate drives:** use F-KR CMMT linear and rotary FMUs through a CiA402 Drive
  profile, or select the existing Copley DriveSim adapter within its supported scope.
- **Simulate remote I/O:** configure CPX-AP-I-EC DI/DO/AI/AO modules and connect
  individual channels to double-acting cylinder or analog-delay FMUs.
- **Use real EtherCAT communication:** discover slaves, access device parameters,
  exchange PDOs and combine virtual devices with physical devices.
- **Keep device settings:** persist axis parameters and the last accepted PDO
  mapping across container recreation, using stable device names.
- **Test fault handling:** retain the EtherCAT slave process when the model host
  fails or stops responding, with defined manual recovery behaviour.

```text
Application / Control Panels
            |
     Motion Server / EtherCAT master
            |
     Physical EtherCAT devices (optional)
            |
     Soft ESC — Linux Docker, end of the line
       EtherCAT Slave Interface (KickCAT)
            |
           IPC
            |
       Functional Model Host
       +-- CiA402 Drive profile -> model adapter -> drive FMU
       +-- Remote I/O profile  -> I/O adapter   -> cylinder / delay FMU
```

The slave interface and functional model host are separate processes. FMUs run
as libraries inside the model host. One logical device OD is shared by the
profile and adapter; the behaviour model calculates motion or physical response.

## Platforms and release status

- **Soft ESC 1.0.0:** the released baseline for current internal and DT Demo work.
- **Runtime:** Linux x86-64 with Docker Engine and Docker Compose. Docker uses host
  networking and the configured EtherCAT NIC. Windows is a validated master/client
  host, not the supported Soft ESC runtime.
- **Validated:** F-KR/Copley axes, CPX and cylinder mixed operation, parameter and
  mapping restoration, and model-host fault isolation on the existing physical bench.
- **Deferred acceptance:** final Demo device configuration and deployment on a new
  Edge PC will be checked together when the Demo equipment is configured.
- **Maintenance policy:** until DT Demo is complete, only TD work fixing bugs or
  deficiencies in implemented features is undertaken. New RF feature implementation
  is frozen. RF-021 follows DT Demo; RF-019/020 are outside the v1.0/Demo scope.

See the [v1.0 release notes](Doc/Releases/v1.0.0.md) and
[maintenance policy](Doc/Design/ADR-011-v1-maintenance-policy.md).

## Getting started

1. Prepare a Linux host, Docker Engine/Compose, Python 3, Git and a dedicated
   EtherCAT NIC. Use a separate engineering network for SSH and management.
2. Clone the release with its KickCAT submodule:

   ```bash
   git clone --branch v1.0.0 --recurse-submodules https://github.com/IlgonKo/ethercat-device-simulator.git
   cd ethercat-device-simulator
   cp .env.example .env
   nano .env
   ```

3. Set the NIC and device layout in `.env`. The supplied example defines four
   F-KR axes; the commented I/O example shows CPX modules and model bindings.
4. Load the prepared release image/offline bundle, or build from the release
   source using the [deployment guide](scripts/deployment/README.md).
   Source builds require the pinned wheels, dependency sources, base/builder
   images and cylinder FMU input described there. A source clone alone does not
   include those binary inputs.
5. Start Soft ESC, then connect and initialize the EtherCAT bus from the master.

The scripts use the local image name `ethercat-device-simulator:dev`. To select
the loaded v1.0 image for these existing scripts:

```bash
docker tag ethercat-device-simulator:1.0.0 ethercat-device-simulator:dev
bash scripts/docker/start.sh
bash scripts/docker/status.sh
bash scripts/docker/logs.sh
```

The versioned image is a local Docker/save-load artifact, not a published registry
image. The GitHub release provides source, F-KR FMUs and the cylinder FMU; it does not
provide the complete offline Docker bundle. Follow the deployment guide for source
builds or a prepared offline bundle. No image is pulled by the commands above.

The [cylinder FMU download](https://github.com/IlgonKo/ethercat-device-simulator/releases/download/v1.0.0/SoftESCDoubleActingCylinder-fmi3-web.fmu)
is the unchanged binary validated with v1.0. Download its companion notices and
`SHA256SUMS-cylinder` from the release assets. Place it in `model_artifacts/` when
preparing source-build inputs; the validated target is Linux x86-64 / FMI 3.0 CS.

## Runtime configuration

All bus and device settings live in the Simulator's own `.env`. It does not read
Motion Server configuration. This example replaces the axis layout in that file:

```ini
KICKCAT_INTERFACE=enp1s0
DEVICE_SIMULATOR_STATE_DIR=./state
DEVICE_SIMULATOR_BUS=0:axis:cia402-drive,1:axis:cia402-drive
DEVICE_SIMULATOR_AXIS_NAMES=0:virtual-axis-0,1:virtual-axis-1
DEVICE_SIMULATOR_AXIS_MODELS=0:f_kr_cmmt,1:f_kr_cmmt
DEVICE_SIMULATOR_AXIS_MODES=0:linear,1:rotary
DEVICE_SIMULATOR_SESSION_TIMEOUT=0
```

- Bus indices are explicit, contiguous Simulator-local indices. The master's
  absolute slave indices also include physical devices earlier in the line.
- Axis names identify `state/<name>.json` and the corresponding mapping file in
  `state/pdo-mappings/`. Keep names stable when reordering devices.
- Changing an axis model/mode does not convert an existing parameter file.
  Incompatible stored data is rejected; it is not silently reset or migrated.
- `SESSION_TIMEOUT=0` runs continuously. A positive value is for diagnostics.
- FMUs are included in the built image. An explicit `DEVICE_SIMULATOR_FMU_DIR`
  overrides that folder and must contain every FMU required by the configuration.

For Remote I/O, use `DEVICE_SIMULATOR_IO_<id>_MODULES`, `IO_MODELS`,
`IO_MODEL_INSTANCES` and station `BINDINGS` as shown in [.env.example](.env.example).
Geometry/delay presets are stored in [model_presets](model_presets/README.md);
operating and initial conditions belong to each configured instance.

## Operation and updates

Run from the repository root:

```bash
bash scripts/docker/start.sh          # Start/recreate with the existing image
bash scripts/docker/status.sh
bash scripts/docker/logs.sh           # Ctrl+C stops log viewing only
bash scripts/docker/stop.sh           # Stop; preserve persistent state
```

After preparing the pinned build inputs, build without starting a container:

```bash
bash scripts/docker/build.sh
```

`start.sh --build` builds and then recreates the container. Ordinary startup does
not rebuild. Before replacing a running simulator, stop motion and disconnect the
master bus, then back up `.env` and the configured state directory. Reconnect and
initialize the master after startup. See the [backup and recovery procedure](scripts/deployment/README.md).

`validate.sh` checks configuration, models and stored data without opening the
EtherCAT NIC; stop the service using that store first. Container health indicates
process readiness, not successful EtherCAT OP state, WKC or motion completion.

## Models and supported boundaries

| Model / device | v1.0 support |
| --- | --- |
| F-KR CMMT | FMI 3.0 Co-Simulation, separate linear/rotary FMUs; PP/PV/Jog, virtual Homing, Stop/Halt/Quick Stop, Disable and Fault Reset policies |
| Copley DriveSim | Existing PP/parameter/Reset integration; no PV/Jog/Homing expansion. Referenced is projected by the adapter; Halt is ignored and Moving B8 differs from F-KR |
| CPX-AP-I-EC | DI/DO/AI/AO, configuration-derived fixed PDOs, mapping/assignment reads and the agreed minimal OD access; no IO-Link |
| Double-acting cylinder | Two DO commands and two end-position DI signals; instance presets and operating/initial conditions |
| Analog delay | Signed Int16 AO-to-AI delay model; no connection to the cylinder's AI/AO channels |

Axis PDO remapping is allowed through individual SDO writes in PRE-OP and is
persisted after acceptance. Duplicate OD mapping and Complete Access are not
supported. CPX mapping is fixed by module configuration and is not writable.

F-KR models reproduce the agreed drive behaviour, not a complete CMMT product or
electrical/torque/load model. Rotary modulo/shortest-path and coordinated-motion
extensions are outside v1.0. Existing CSP behaviour was regression-tested offline;
this release does not claim real-time performance or complete EtherCAT/CiA402
conformance. Analog FMU tests passed offline; the manual/physical end-to-end
analog test was explicitly omitted from the agreed acceptance scope.

## Fault handling and recovery

Correct the cause of a supported axis fault before requesting Fault Reset through
the master. Fault Reset does not recreate a failed FMU or recover a stopped model
host. Model-host timeout/failure requires manual container restart and master
reinitialization; operation does not resume automatically. F-KR axes require
Homing again after model recreation.

I/O model execution errors remain internal diagnostics. They are not translated
into CPX device errors. Application timeouts, interlocks and process fault policy
belong to the application using the I/O.

## Documentation

- [Release scope and validation](Doc/Releases/v1.0.0.md)
- [Docker/offline deployment](scripts/deployment/README.md) and [script guide](scripts/README.md)
- [Architecture decisions](Doc/Design/README.md) and [project layout](Doc/Design/ADR-010-project-layout.md)
- [RF status](Doc/RF/README.md), [TD tracking](Doc/TD/README.md), [work log](Doc/Work_log.md)
- [Project plan](Doc/project-plan.md) and [DT Demo requirements](Doc/DT-demo-gap-analysis.md)
- [Axis policies](Doc/RF/RF-015-axis-model-semantics.md), [I/O contract](Doc/RF/RF-013-virtual-io.md)
- [F-KR FMU source/build](model_sources/motor_controller/f_kr_cmmt/README.md),
  [Copley](model_sources/motor_controller/copley/README.md),
  [cylinder](model_sources/pneumatic_cylinder/double_acting/README.md)

## Folder guide

```text
src/ethercat_slave/    KickCAT interface, mailbox, PDO mapping and model IPC
src/functional_model/ Device profiles, adapters, FMI execution, storage and diagnostics
device_descriptions/  Product identity, ESI and device-specific OD metadata
model_sources/        Behaviour-model sources and reproducible build inputs/metadata
model_presets/        Reusable model settings
model_artifacts/      Generated or supplied FMUs (not committed)
protocols/            Cross-process contracts
scripts/              Docker operation, deployment, model builds and validation
state/                Local persistent device data (not committed)
tests/                Unit, native and integration tests; frozen comparison model
Doc/                  Requirements, decisions, validation records and release notes
third_party/KickCAT/   Pinned upstream submodule
build/ .cache/ results/ Local build, download and test outputs (not release source)
```
