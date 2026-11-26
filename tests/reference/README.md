# RF-022 reference

`servo_model.py`, `state_machine.py` and the Python adapter are preserved from
RF-015 commit `88d7f40a30fb0733d14f674c9be10847b2f18bf9`.
Only adapter imports were redirected to make the reference explicitly test-only.
`factory.py` injects this reference into the common runtime for the existing
RF-015 policy tests. Production never selects it as a fallback.
Actual FMU tests send identical public OD commands and calculation intervals to
both adapters; no private model state is injected into the FMU.
