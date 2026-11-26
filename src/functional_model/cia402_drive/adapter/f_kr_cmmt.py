import math
import os
from pathlib import Path
from functional_model.runtime.fmi.runner import Fmi3Runner
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

    def __init__(self, profile, od=None, artifact=None, instance_name="f_kr_cmmt"):
        self.profile = profile
        od = od if od is not None else ConfiguredObjectDictionary(profile)
        od.overlay(0x605A, name="Quick stop option code", data_type="int16",
                   bit_size=16, access="rw", default=2)
        od.overlay(0x6085, name="Quick stop deceleration", data_type="uint32",
                   bit_size=32, access="rw", default=int(od.read(0x6084)))
        # Expose Quick Stop settings independently of the default PDO mapping.
        self.additional_od_keys = ((0x605A, 0), (0x6085, 0))
        self.units = FKrUnits(od)
        self.od = od
        self.persistent_roles = profile.persistent_roles + tuple(
            r for r in profile.pdo_configuration.rx if (r.index, r.subindex) == (0x6081, 0))
        self.persistent_roles += tuple(SimpleNamespace(index=index, subindex=sub)
                                       for index, sub in self.additional_od_keys)
        install_role_index(self.od)
        self.bridge = VirtualOdBridge(self.od, profile.pdo_configuration)
        mode = 'rotary' if profile.description.preset == 'rotary_deg' else 'linear'
        self.angular_scale = math.pi / 180 if mode == 'rotary' else 1.0
        if artifact is None:
            folder = Path(os.environ.get('DEVICE_SIMULATOR_FMU_DIR', Path(__file__).resolve().parents[4] / 'model_artifacts'))
            artifact = folder / ('FKrCmmt' + mode.title() + '-linux.fmu')
        self._last_reset = int(self.od.read_role('device_reset_command'))
        self._last_save = int(self.od.read_role('parameter_save_command'))
        self._previous_control_word = int(self.od.read(0x6040))
        self._last_csp_target = self.od.read(0x607A)
        signature = {name: (kind, 'input') for name, kind, _, _ in INPUTS}
        signature.update({name: (kind, 'output') for name, kind in OUTPUTS})
        self.runner = Fmi3Runner(artifact, signature, instance_name, initial_values=self._inputs())
        if self.runner.variables['actual_position'].unit != ('rad' if mode == 'rotary' else 'm'):
            self.runner.close()
            raise ValueError('F-KR FMU physical dimension does not match axis mode')
        self.od.write_internal(0x6061, self.runner.get('mode_display'))


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

    def _inputs(self):
        values = {}
        for name, kind, index, sub in INPUTS:
            value = self.units.read(index, sub)
            if kind == 'Float64':
                value = value / 1000 if name == 'position_window_time' else value * self.angular_scale
                if name in ('positive_velocity_limit', 'negative_velocity_limit'): value = abs(value)
            else:
                value = int(value)
            values[name] = value
        return values

    def _od_commands(self):
        reset = int(self.od.read_role('device_reset_command'))
        if reset == 1 and reset != self._last_reset:
            position = self.od.read(0x6064)
            self.od.reset_non_pdo_configuration()
            self.od.reset_pdo_values()
            self.od.write_internal(0x607A, position)
            self.od.write_internal(0x6064, position)
        self._last_reset = reset
        save = int(self.od.read_role('parameter_save_command'))
        if save == 1 and save != self._last_save:
            for role, value in [('parameter_save_status', 0), ('parameter_save_return_code', 0), ('parameter_save_return_value', 1)]:
                self.od.write_role(role, value)
        self._last_save = save

    def deactivate(self):
        # A valid disable step cancels accepted motion; no wall-time catch-up.
        self.od.write_internal(0x6040, 0)
        self.step(.001)

    def step(self, dt):
        self._od_commands()
        before_status = self.od.read(0x6041)
        target = self.od.read(0x607A)
        for name, value in self._inputs().items():
            self.runner.set(name, value)
        self.runner.step(dt)
        status = self.runner.get('status_word')
        mode = self.runner.get('mode_display')
        position = self.runner.get('actual_position') / self.angular_scale
        velocity = self.runner.get('actual_velocity') / self.angular_scale
        # Unit conversion rejects nonfinite feedback; PDO/SDO encoding checks raw range.
        self.units.write(0x6064, position)
        self.units.write(0x606C, velocity)
        self.od.write_internal(0x6041, status)
        self.od.write_internal(0x6061, mode)
        cw = int(self.od.read(0x6040))
        home_start_edge = bool(cw & 0x10) and not self._previous_control_word & 0x10
        if mode == 6 and status & 0x8400 == 0x8400 and (
                not before_status & 0x8000 or before_status & 0x100 or home_start_edge):
            self.od.write_internal(0x607A, 0)
        self._previous_control_word = cw
        if mode == 8 and (status & 0x6f) == 0x27:
            if target != self._last_csp_target:
                if not before_status & 0x8000:
                    self.od.write_internal(0x607A, self._last_csp_target)
                elif not self.od.read(0x607D, 1) <= target <= self.od.read(0x607D, 2):
                    self.od.write_internal(0x607A, self.od.read(0x6064))
                self._last_csp_target = self.od.read(0x607A)

    def read_inputs(self): return self.bridge.od_to_txpdo_payload()

    def close(self): self.runner.close()


INPUTS = (
    ('control_word', 'UInt16', 0x6040, 0), ('mode_request', 'Int8', 0x6060, 0),
    ('quick_stop_option', 'Int16', 0x605A, 0), ('target_position', 'Float64', 0x607A, 0),
    ('target_velocity', 'Float64', 0x60FF, 0), ('profile_velocity', 'Float64', 0x6081, 0),
    ('profile_acceleration', 'Float64', 0x6083, 0), ('profile_deceleration', 'Float64', 0x6084, 0),
    ('quick_stop_deceleration', 'Float64', 0x6085, 0), ('position_min', 'Float64', 0x607D, 1),
    ('position_max', 'Float64', 0x607D, 2), ('positive_velocity_limit', 'Float64', 0x607F, 0),
    ('negative_velocity_limit', 'Float64', 0x2183, 12), ('position_window', 'Float64', 0x6067, 0),
    ('position_window_time', 'Float64', 0x6068, 0),
)
OUTPUTS = (('status_word', 'UInt16'), ('mode_display', 'Int8'),
           ('actual_position', 'Float64'), ('actual_velocity', 'Float64'))
