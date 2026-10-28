"""PP adapter. Runtime Fault projection and IPC isolation live outside the FMU."""
import math
from functional_model.cia402_drive.profile.configured_od import ConfiguredObjectDictionary
from functional_model.cia402_drive.profile.bridge import VirtualOdBridge
from functional_model.cia402_drive.profile.codec import decode_od_value
from functional_model.cia402_drive.profile.capabilities import DriveCapabilities
from functional_model.cia402_drive.model_definitions.copley_drive_sim import SIGNATURE, STEP_SECONDS
from functional_model.runtime.fmi.runner import Fmi3Runner
from .errors import DeviceRejectedException


class CopleyAdapter:
    capabilities = DriveCapabilities(frozenset({1}))
    WRITABLE = {(0x6040, 0), (0x6060, 0), (0x607A, 0), (0x6081, 0),
                (0x6083, 0), (0x6084, 0), (0x2005, 1), (0x2005, 3), (0x2000, 1)}

    def __init__(self, profile, runner):
        self.profile, self.runner = profile, runner
        self.od = ConfiguredObjectDictionary(profile)
        self.bridge = VirtualOdBridge(self.od, profile.pdo_configuration)
        self._remainder = 0.0
        self._fault = False
        self.od.write_internal(0x6060, 1)
        self.od.write_internal(0x6061, 1)
        # Both models use raw OD position counts. Derive velocity/acceleration
        # conversion from existing unit exponents, without another scale setting.
        scale = lambda sub: 10.0 ** (-abs(self.od.read(0x2194, sub)))
        self.velocity_factor = scale(2) / scale(1)
        self.acceleration_factor = scale(3) / scale(1)
        self.od.write_internal(0x6081, round(runner.get('ProfileVelocity') / self.velocity_factor))
        acceleration = round(runner.get('ProfileAcceleration') / self.acceleration_factor)
        self.od.write_internal(0x6083, acceleration)
        self.od.write_internal(0x6084, acceleration)
        # Persist only parameters actually applied by this model plus unit metadata.
        keys = {(0x216E, 1), *((0x2194, sub) for sub in range(1, 5)),
                (0x6081, 0), (0x6083, 0), (0x6084, 0)}
        candidates = profile.roles + profile.pdo_configuration.rx
        self.persistent_roles = tuple(r for r in candidates if (r.index, r.subindex) in keys)
        self._refresh()

    @staticmethod
    def validate_parameters(values):
        for key in ((0x6081, 0), (0x6083, 0), (0x6084, 0)):
            if values[key] <= 0:
                raise ValueError('Copley profile parameters must be positive')
        if values[0x6083, 0] != values[0x6084, 0]:
            raise ValueError('Copley requires equal profile acceleration and deceleration')

    @classmethod
    def open(cls, profile, artifact, instance_name='copley'):
        runner = Fmi3Runner(artifact, SIGNATURE, instance_name)
        try:
            return cls(profile, runner)
        except Exception:
            runner.close()
            raise

    def close(self): self.runner.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def read_sdo(self, index, subindex, size):
        return self.bridge.read_sdo(index, subindex, size)

    @staticmethod
    def _validate(index, value):
        if index == 0x6060 and value not in (0, 1):
            raise DeviceRejectedException('Copley initial adapter supports PP only')
        if index in (0x6081, 0x6083, 0x6084) and value <= 0:
            raise DeviceRejectedException('Profile velocity/acceleration must be positive')

    def write_sdo(self, index, subindex, payload):
        if (index, subindex) not in self.WRITABLE:
            raise DeviceRejectedException(f'Unsupported Copley write {index:04x}:{subindex}')
        definition = self.od.definition(index, subindex)
        if len(payload) != definition.bit_size // 8:
            raise ValueError('SDO length mismatch')
        value = decode_od_value(definition.data_type, payload)
        if (index, subindex) == (0x2000, 1) and value != 0:
            raise DeviceRejectedException('Device restart is not supported; only command clear (0) is supported')
        self._validate(index, value)
        self.bridge.write_sdo(index, subindex, payload)

    def apply_outputs(self, payload):
        if len(payload) != sum(x.byte_length for x in self.profile.pdo_configuration.rx):
            raise ValueError('RxPDO length mismatch')
        offset = 0
        for entry in self.profile.pdo_configuration.rx:
            raw = payload[offset:offset + entry.byte_length]
            offset += entry.byte_length
            if not entry.index: continue
            value = decode_od_value(entry.data_type, raw)
            self._validate(entry.index, value)
            if entry.index in (0x60FF, 0x6071, 0x60B1, 0x60B2) and value:
                raise DeviceRejectedException('Nonzero velocity/torque/offset input unsupported in PP')
        self.bridge.rxpdo_payload_to_od(payload)

    def inject_fault(self, active):
        """Offline test hook, not a manufacturer OD object."""
        self._fault = bool(active)

    def step(self, dt):
        if not math.isfinite(dt) or not 0 < dt <= 0.1:
            raise ValueError('Model dt must be in (0, 0.1] seconds')
        if self._fault and self.od.read(0x6040) & 0x80:
            raise DeviceRejectedException('Fault injection is still active')
        acceleration, deceleration = self.od.read(0x6083), self.od.read(0x6084)
        # Permit sequential SDO updates, but never execute with an unequal pair.
        if acceleration != deceleration:
            raise DeviceRejectedException('Copley requires equal profile acceleration and deceleration')
        for index in (0x6040, 0x6060, 0x6081, 0x6083, 0x6084):
            self._validate(index, self.od.read(index))
        # Halt is intentionally unsupported: preserve raw OD, ignore only bit 8 at the FMU boundary.
        values = {'ControlWord': self.od.read(0x6040) & ~0x0100, 'ModesOfOp': self.od.read(0x6060),
                  'TargetPosition': self.od.read(0x607A), 'TargetVelocity': 0,
                  'TargetTorque': 0, 'FaultInject': self._fault,
                  'ProfileVelocity': self.od.read(0x6081) * self.velocity_factor,
                  'ProfileAcceleration': acceleration * self.acceleration_factor}
        for name, value in values.items(): self.runner.set(name, value)
        self._remainder += dt
        while self._remainder + 1e-12 >= STEP_SECONDS:
            self.runner.step(STEP_SECONDS)
            self._remainder = max(0.0, self._remainder - STEP_SECONDS)
        self._refresh()

    def _refresh(self):
        # CMMT compatibility referenced bit only; never synthesize bit12/bit13.
        self.od.write_internal(0x6041, self.runner.get('StatusWord') | 0x8000)
        for index, name in ((0x6061, 'ModesDisplay'), (0x6064, 'ActualPosition'),
                            (0x6077, 'TorqueActual')):
            self.od.write_internal(index, self.runner.get(name))
        self.od.write_internal(0x606C, round(self.runner.get('ActualVelocity') * 0.1 / self.velocity_factor))

    def read_inputs(self): return self.bridge.od_to_txpdo_payload()
