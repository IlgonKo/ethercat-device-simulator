import struct
import unittest
from device_descriptions.cmmt_as.description import CmmtAsDescription
from functional_model.cia402_drive.profile.profile import CiA402DriveProfile
from functional_model.cia402_drive.adapter.copley import CopleyAdapter
from functional_model.cia402_drive.adapter.errors import DeviceRejectedException


class FakeRunner:
    def __init__(self):
        self.values = dict(StatusWord=0x250, ModesDisplay=1, ActualPosition=0,
                           ActualVelocity=0, TorqueActual=0, ProfileVelocity=100000.,
                           ProfileAcceleration=500000.)
        self.steps = []
    def get(self, name): return self.values[name]
    def set(self, name, value): self.values[name] = value
    def step(self, dt): self.steps.append(dt)
    def close(self): pass


class CopleyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.runner = FakeRunner()
        self.adapter = CopleyAdapter(CiA402DriveProfile(CmmtAsDescription('linear')), self.runner)

    def test_only_referenced_bit_is_added(self):
        for status in (0x250, 0x27, 0x1027, 0x8):
            self.runner.values['StatusWord'] = status
            self.adapter.step(.008)
            self.assertEqual(self.adapter.od.read(0x6041), status | 0x8000)

    def test_unit_conversion_and_fixed_steps(self):
        a = self.adapter
        a.write_sdo(0x6081, 0, (1234).to_bytes(4, 'little'))
        self.runner.values['ActualVelocity'] = 1000
        a.step(.003)
        a.step(.005)
        self.assertEqual(self.runner.steps, [.002] * 4)
        self.assertEqual(self.runner.values['ProfileVelocity'], 1234 * a.velocity_factor)
        self.assertEqual(a.od.read(0x606C), round(100 / a.velocity_factor))

    def test_reject_mode_before_changing_od(self):
        a = self.adapter
        for mode in (3, 4, 6, 8):
            with self.assertRaises(DeviceRejectedException): a.write_sdo(0x6060, 0, bytes([mode]))
            payload = struct.pack('<HbiIihihB', 15, mode, 99, 100, 0, 0, 0, 0, 0)
            with self.assertRaises(DeviceRejectedException): a.apply_outputs(payload)
        self.assertEqual(a.od.read(0x6040), 0)
        self.assertEqual(a.od.read(0x607A), 0)

    def test_acceleration_pair_requires_consistency_at_step(self):
        a = self.adapter
        a.write_sdo(0x6083, 0, (2000).to_bytes(4, 'little'))
        with self.assertRaises(DeviceRejectedException): a.step(.008)
        self.assertFalse(self.runner.steps)
        a.write_sdo(0x6084, 0, (2000).to_bytes(4, 'little'))
        a.step(.008)
        self.assertEqual(self.runner.values['ProfileAcceleration'], 2000 * a.acceleration_factor)

    def test_unsupported_writes_and_invalid_dt(self):
        for index, sub, payload in ((0x607D, 1, b'\0'*4), (0x6041, 0, b'\0'*2),
                                    (0x6081, 0, b'\0'*4)):
            with self.assertRaises(DeviceRejectedException): self.adapter.write_sdo(index, sub, payload)
        for dt in (0, -.001, .101, float('nan')):
            with self.assertRaises(ValueError): self.adapter.step(dt)

    def test_halt_is_ignored_only_at_fmu_boundary(self):
        a = self.adapter
        for cw in (0x0106, 0x0107, 0x010f, 0x013f, 0x017f, 0x0180, 0x000f):
            a.write_sdo(0x6040, 0, cw.to_bytes(2, 'little'))
            a.step(.008)
            self.assertEqual(a.od.read(0x6040), cw)
            self.assertEqual(self.runner.values['ControlWord'], cw & ~0x100)
            a.apply_outputs(struct.pack('<HbiIihihB', cw, 1, 1000, 100, 0, 0, 0, 0, 0))
            a.step(.008)
            self.assertEqual(a.od.read(0x6040), cw)
            self.assertEqual(self.runner.values['ControlWord'], cw & ~0x100)
