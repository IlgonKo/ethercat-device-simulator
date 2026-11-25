# FMU artifacts

`copley_drive_sim` loads `CopleyDriveSim-linux.fmu` from this directory.
Use `DEVICE_SIMULATOR_FMU_DIR` to change the host directory. Docker mounts it
read-only at `/model_artifacts`. FMU binaries are not committed.

Build on Linux x86_64:

```bash
build/fmi-venv/bin/python scripts/linux/build-copley-fmu.py \
  --output model_artifacts/CopleyDriveSim-linux.fmu
```

Copley integration and IPC fault isolation evidence is recorded in RF-017/RF-018.

## Pneumatic cylinder — offline validated, IO integration pending

`SoftESCDoubleActingCylinder-fmi3-web.fmu` is the selected FMI 3.0 Co-Simulation
artifact exported from OpenModelica Playground. Its Linux x86-64 binary passed
five offline cases on 2026-11-25. It is not registered as an operational Soft ESC model yet.

- SHA256: `34b14a7967042fe3abaabab4de6086e8a29324faeb3a2ab29f569c590e2cac42`.
- Preserve the complete FMU archive, including its resources and companion binary files.
- [Source / export instructions](../model_sources/pneumatic_cylinder/README.md).
- [Linux validation](../Doc/Validation/Pneumatic-Cylinder-Web-FMU-20261125.md).
- FMU binaries remain outside Git; source, upstream pin, scripts and validation hashes are tracked.
  A newly exported artifact must be validated again.

`SoftESCDoubleActingCylinder-win64.fmu` is the earlier, separately built FMI 2.0
Windows test artifact. Its substep/solver constraints do not describe the selected FMI 3.0 file.
