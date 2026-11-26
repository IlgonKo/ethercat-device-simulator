# Copley motor controller model

The upstream package is a source FMU with generated C code, not a Modelica source.
`upstream.json` pins its source and hash. Preserve upstream notices when redistributing;
this folder does not grant a new license or assert manufacturer certification.

Build: `python3 scripts/models/build-copley-fmu.py --source .cache/downloads/copley/CopleyDriveSim-source.fmu --output model_artifacts/CopleyDriveSim-linux.fmu`

Run this command from the repository root. The build script reads this metadata and
checks the source hash. Downloaded sources belong in .cache, extracted build files in
build, and validated full FMUs in model_artifacts. Runtime adapters stay in src.
