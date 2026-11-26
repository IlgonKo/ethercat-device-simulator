from functional_model.cia402_drive.behaviour_model.f_kr_cmmt.servo_model import VirtualCiA402Servo
from functional_model.cia402_drive.behaviour_model.f_kr_cmmt.od_role_index import install_role_index
from functional_model.cia402_drive.profile.bridge import VirtualOdBridge
from functional_model.cia402_drive.profile.capabilities import DriveCapabilities
from .errors import DeviceRejectedException
from .f_kr_units import FKrUnits
from types import SimpleNamespace
from functional_model.cia402_drive.profile.configured_od import ConfiguredObjectDictionary
from functional_model.cia402_drive.profile.codec import decode_od_value

class FKrCmmtAdapter:
    capabilities = DriveCapabilities(frozenset({1, 3, 6, 8, -3}))

    def __init__(self, profile, od=None):
        self.profile = profile
        od = od if od is not None else ConfiguredObjectDictionary(profile)
        od.overlay(0x605A, name="Quick stop option code", data_type="int16",
                   bit_size=16, access="rw", default=2)
        od.overlay(0x6085, name="Quick stop deceleration", data_type="uint32",
                   bit_size=32, access="rw", default=int(od.read(0x6084)))
        # Expose Quick Stop settings independently of the default PDO mapping.
        self.additional_od_keys = ((0x605A, 0), (0x6085, 0))
        self.units = FKrUnits(od)
        self.model = VirtualCiA402Servo(cycle_time=0.01, device_profile=profile, od=od, units=self.units)
        self.od = self.model.od
        self.persistent_roles = profile.persistent_roles + tuple(
            r for r in profile.pdo_configuration.rx if (r.index, r.subindex) == (0x6081, 0))
        self.persistent_roles += tuple(SimpleNamespace(index=index, subindex=sub)
                                       for index, sub in self.additional_od_keys)
        install_role_index(self.od)
        self.bridge = VirtualOdBridge(self.od, profile.pdo_configuration)

    def read_sdo(self, index, subindex, size):
        return self.bridge.read_sdo(index, subindex, size)

    def validate_mode(self, mode):
        # Zero is a valid idle/unselected input; no unsupported mode is executed.
        if mode != 0 and mode not in self.capabilities.modes:
            raise DeviceRejectedException(f'Unsupported mode {mode}')

    @staticmethod
    def validate_parameters(values):
        if values[(0x607D, 1)] > values[(0x607D, 2)]:
            raise ValueError("Minimum position limit exceeds maximum")
        if values[(0x605A, 0)] != 2 or values[(0x6085, 0)] <= 0:
            raise ValueError("Invalid Quick Stop configuration")

    def write_sdo(self, index, subindex, payload):
        definition = self.od.definition(index, subindex)
        if len(payload) != definition.bit_size // 8:
            raise ValueError("SDO length mismatch")
        value = decode_od_value(definition.data_type, payload)
        if (index, subindex) == (0x6060, 0):
            self.validate_mode(value)
        elif index == 0x607D and subindex in (1, 2):
            lo = value if subindex == 1 else self.od.read(index, 1)
            hi = value if subindex == 2 else self.od.read(index, 2)
            if lo > hi:
                raise ValueError("Minimum position limit exceeds maximum")
        elif (index, subindex) == (0x605A, 0) and value != 2:
            raise ValueError("Only Quick Stop option 2 is supported")
        elif (index, subindex) == (0x6085, 0) and value <= 0:
            raise ValueError("Quick Stop deceleration must be positive")
        self.bridge.write_sdo(index, subindex, payload)

    def apply_outputs(self, payload, keys=None):
        expected = sum(x.byte_length for x in self.profile.pdo_configuration.rx)
        if len(payload) != expected: raise ValueError('RxPDO length mismatch')
        offset = 0
        for entry in self.profile.pdo_configuration.rx:
            if (entry.index, entry.subindex) == (0x6060, 0) and (keys is None or (entry.index, entry.subindex) in keys):
                self.validate_mode(int.from_bytes(payload[offset:offset+entry.byte_length], 'little', signed=True))
            offset += entry.byte_length
        self.bridge.rxpdo_payload_to_od(payload, keys=keys)

    def deactivate(self):
        target = self.od.read(0x607A)
        self.model.stop_at_current_position()
        # Complete the disable transition before the next enable sequence.
        self.od.write_internal(0x6040, 0)
        self.model.process_cycle()
        self.od.write_internal(0x607A, target)
        self.model._last_target_position_command = self.units.read(0x607A)
        self.model.previous_controlword = 0
        self.model.pp_active = False
        self.model.pp_setpoint_ack = False

    def step(self, dt):
        self.model.cycle_time = dt
        self.model.model_update()

    def read_inputs(self): return self.bridge.od_to_txpdo_payload()
