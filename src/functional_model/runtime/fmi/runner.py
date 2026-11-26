"""FMI 3 Co-Simulation runner for synchronous, scalar, fixed-step models.

Native calls run in the model host. This class does not isolate native crashes or
interrupt a hanging doStep; EtherCAT fault isolation is a separate work item.
"""
import math
import tempfile
from numbers import Integral, Real


class Fmi3Runner:
    def __init__(self, artifact, signature, instance_name='drive', *, initial_values=None):
        from fmpy import extract, read_model_description
        from fmpy.fmi3 import FMU3Slave
        self._folder = tempfile.TemporaryDirectory(prefix='softesc-fmu-')
        self._fmu = None
        self._initialized = False
        self.failed = False
        self.time = 0.0
        try:
            md = read_model_description(str(artifact), validate=True)
            if md.fmiVersion != '3.0' or md.coSimulation is None:
                raise ValueError('Requires FMI 3.0 Co-Simulation')
            self.variables = {v.name: v for v in md.modelVariables}
            for name, (kind, causality) in signature.items():
                v = self.variables.get(name)
                if v is None or (v.type, v.causality) != (kind, causality) or v.dimensions:
                    raise ValueError(f'FMU variable contract mismatch: {name}')
            extract(str(artifact), unzipdir=self._folder.name)
            self._fmu = FMU3Slave(guid=md.guid, modelIdentifier=md.coSimulation.modelIdentifier,
                                 unzipDirectory=self._folder.name, instanceName=instance_name)
            self._fmu.instantiate(eventModeUsed=False, earlyReturnAllowed=False)
            self._fmu.enterInitializationMode(startTime=0.0)
            for name, value in (initial_values or {}).items():
                self._write(name, value, initializing=True)
            self._fmu.exitInitializationMode()
            self._initialized = True
        except Exception:
            self.close()
            raise

    def _check(self):
        if not self._initialized or self.failed:
            raise RuntimeError('FMU is closed or failed; create a new instance')

    def set(self, name, value):
        self._check()
        self._write(name, value, initializing=False)

    def _write(self, name, value, *, initializing):
        if name not in self.variables:
            raise ValueError(f'Unknown FMU setting: {name}')
        v = self.variables[name]
        if v.causality not in ('input', 'parameter'):
            raise ValueError(f'Not writable: {name}')
        if v.causality == 'parameter' and not initializing and getattr(v, 'variability', 'fixed') != 'tunable':
            raise ValueError(f'FMU parameter is initialization-only in this runner: {name}')
        if v.type.startswith('Float'):
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f'Finite FMU real required: {name}')
        elif v.type.startswith(('Int', 'UInt')):
            bits = int(v.type.lstrip('UInt'))
            signed = v.type.startswith('Int')
            low, high = (-(1 << (bits-1)), (1 << (bits-1))-1) if signed else (0, (1 << bits)-1)
            if isinstance(value, bool) or not isinstance(value, Integral) or not low <= value <= high:
                raise ValueError(f'FMU integer out of range: {name}')
        elif v.type == 'Boolean':
            if not isinstance(value, bool):raise ValueError(f'FMU Boolean required: {name}')
        else:
            raise ValueError(f'Unsupported scalar FMU type: {v.type}')
        for attribute, comparison in [('min', lambda a,b:a<b), ('max', lambda a,b:a>b)]:
            bound = getattr(v, attribute, None)
            if bound is not None and comparison(value, float(bound)):
                raise ValueError(f'FMU value violates {attribute}: {name}')
        try:
            getattr(self._fmu, 'set' + v.type)([v.valueReference], [value])
        except Exception:
            self.failed = True
            raise

    def get(self, name):
        self._check()
        v = self.variables[name]
        try:
            return getattr(self._fmu, 'get' + v.type)([v.valueReference])[0]
        except Exception:
            self.failed = True
            raise

    def step(self, dt):
        self._check()
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('FMU step must be finite and positive')
        try:
            event, terminate, early, _ = self._fmu.doStep(self.time, dt)
            if event or terminate or early:
                raise RuntimeError('FMU requested unsupported event/termination/early return')
            self.time += dt
        except Exception:
            self.failed = True
            raise

    def close(self):
        fmu, self._fmu = self._fmu, None
        try:
            if fmu is not None:
                try:
                    if self._initialized and not self.failed:
                        fmu.terminate()
                finally:
                    if getattr(fmu, 'component', None):
                        fmu.freeInstance()
        finally:
            self._initialized = False
            self._folder.cleanup()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
