# FMU artifacts

`copley_drive_sim` loads `CopleyDriveSim-linux.fmu` from this directory.
Use `DEVICE_SIMULATOR_FMU_DIR` to change the host directory. Docker mounts it
read-only at `/model_artifacts`. FMU binaries are not committed.

Build on Linux x86_64:

```bash
build/fmi-venv/bin/python scripts/linux/build-copley-fmu.py \
  --output model_artifacts/CopleyDriveSim-linux.fmu
```

The current configuration supports model loading and offline validation.
Physical Copley operation still requires IPC fault isolation; see RF-017.
