from functional_model.cia402_drive.behaviour_model.f_kr_cmmt.servo_model import VirtualCiA402Servo
from functional_model.cia402_drive.behaviour_model.f_kr_cmmt.od_role_index import install_role_index
from functional_model.cia402_drive.profile.bridge import VirtualOdBridge
from functional_model.cia402_drive.profile.capabilities import DriveCapabilities
from .errors import DeviceRejectedException

class FKrCmmtAdapter:
    capabilities = DriveCapabilities(frozenset({1, 3, 6, 8, -3}))

    def __init__(self, profile, od=None):
        self.profile = profile
        self.model = VirtualCiA402Servo(cycle_time=0.01, device_profile=profile, od=od)
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
        # Complete the disable transition now. Otherwise the next enable sequence
        # disables an internally still-enabled drive and overwrites the saved target.
        self.od.write_internal(0x6040, 0)
        self.model.process_cycle()
        self.od.write_internal(0x607A, target)
        self.model._last_target_position_command = target
        self.model.previous_controlword = 0
        self.model.pp_active = False
        self.model.pp_setpoint_ack = False

    def step(self, dt):
        self.model.cycle_time = dt
        self.model.model_update()

    def read_inputs(self): return self.bridge.od_to_txpdo_payload()
