from functional_model.cia402_drive.behaviour_model.f_kr_cmmt.servo_model import VirtualCiA402Servo
from functional_model.cia402_drive.behaviour_model.f_kr_cmmt.od_role_index import install_role_index
from functional_model.cia402_drive.profile.bridge import VirtualOdBridge
from functional_model.cia402_drive.profile.capabilities import DriveCapabilities
from .errors import DeviceRejectedException

class FKrCmmtAdapter:
    capabilities = DriveCapabilities(frozenset({1, 3, 6, 8, -3}))

    def __init__(self, profile):
        self.profile = profile
        self.model = VirtualCiA402Servo(cycle_time=0.01, device_profile=profile)
        self.od = self.model.od
        self.persistent_roles = profile.persistent_roles + tuple(
            r for r in profile.pdo_configuration.rx if (r.index, r.subindex) == (0x6081, 0))
        install_role_index(self.od)
        self.bridge = VirtualOdBridge(self.od, profile.pdo_configuration)

    def read_sdo(self, index, subindex, size):
        return self.bridge.read_sdo(index, subindex, size)

    def validate_mode(self, mode):
        # Zero is a valid idle/unselected input; no unsupported mode is executed.
        if mode != 0 and mode not in self.capabilities.modes:
            raise DeviceRejectedException(f'Unsupported mode {mode}')

    def write_sdo(self, index, subindex, payload):
        if (index, subindex) == (0x6060, 0):
            self.validate_mode(int.from_bytes(payload, 'little', signed=True))
        self.bridge.write_sdo(index, subindex, payload)

    def apply_outputs(self, payload):
        expected = sum(x.byte_length for x in self.profile.pdo_configuration.rx)
        if len(payload) != expected: raise ValueError('RxPDO length mismatch')
        offset = 0
        for entry in self.profile.pdo_configuration.rx:
            if (entry.index, entry.subindex) == (0x6060, 0):
                self.validate_mode(int.from_bytes(payload[offset:offset+entry.byte_length], 'little', signed=True))
            offset += entry.byte_length
        self.bridge.rxpdo_payload_to_od(payload)

    def step(self, dt):
        self.model.cycle_time = dt
        self.model.model_update()

    def read_inputs(self): return self.bridge.od_to_txpdo_payload()
