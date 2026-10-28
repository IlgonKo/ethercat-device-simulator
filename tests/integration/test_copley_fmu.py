"""Actual native FMU tests. Set COPLEY_TEST_FMU to a built Linux artifact."""
import os
import struct
import unittest
import tempfile
from pathlib import Path
from device_descriptions.cmmt_as.description import CmmtAsDescription
from functional_model.cia402_drive.profile.profile import CiA402DriveProfile
from functional_model.cia402_drive.adapter.copley import CopleyAdapter


@unittest.skipUnless(os.environ.get('COPLEY_TEST_FMU'), 'COPLEY_TEST_FMU is not set')
class CopleyFmuTests(unittest.TestCase):
    def test_runtime_fault_reset_matches_motion_server_sequence(self):
        from functional_model.runtime.axis import Model
        from unittest.mock import patch
        m = Model(dict(slave_index=0, id='fault-test', type='cia402-drive', parameter_set='temporary',
                       model=dict(type='copley_drive_sim', mode='linear',
                                  artifact=str(Path(os.environ['COPLEY_TEST_FMU']).resolve()))))
        self.addCleanup(m.close)
        tick = 10.0
        def run(cw, mode=1, target=2000):
            nonlocal tick
            tick += .008
            payload = struct.pack('<HbiIihihB', cw, mode, target, m.adapter.od.read(0x6081), 0, 0, 0, 0, 0)
            with patch('functional_model.runtime.axis.time.monotonic', return_value=tick):
                r = m.dispatch(dict(op='cycle', data=payload.hex()))
            return struct.unpack('<HbiihB', bytes.fromhex(r['data']))
        for cw in (6, 7, 15): run(cw)
        run(0x3f)
        m.adapter.inject_fault(True)
        self.assertTrue(run(15)[0] & 8)
        # Cause remains: reset is acknowledged, but Fault cannot clear.
        self.assertTrue(run(0x8f)[0] & 8)
        self.assertTrue(run(15)[0] & 8)
        m.adapter.inject_fault(False)
        self.assertTrue(run(15)[0] & 8)
        for cw in [15]*2 + [0x8f]*2 + [15]*2 + [6]*5 + [7]*5: result = run(cw)
        self.assertEqual(result[0] & 0x6f, 0x23)
        position = result[2]
        for _ in range(5): self.assertEqual(run(15)[2], position)
        self.assertEqual(run(15)[0] & 0x6f, 0x27)
        self.assertTrue(run(0x3f)[0] & 0x1000)
        self.assertFalse(run(15)[0] & 0x1000)
        # Adapter rejection is isolated and corrected via the same Reset path.
        self.assertTrue(run(15, mode=99)[0] & 8)
        run(15)
        for cw in [0x8f]*2 + [15]*2 + [6]*5 + [7]*5 + [15]*3: result = run(cw)
        self.assertEqual(result[0] & 0x6f, 0x27)

    def open(self, mode='linear'):
        a = CopleyAdapter.open(CiA402DriveProfile(CmmtAsDescription(mode)), os.environ['COPLEY_TEST_FMU'])
        self.addCleanup(a.close)
        return a

    def cycle(self, a, cw, target=0):
        velocity = a.od.read(0x6081)
        a.apply_outputs(struct.pack('<HbiIihihB', cw, 1, target, velocity, 0, 0, 0, 0, 0))
        a.step(.008)
        return struct.unpack('<HbiihB', a.read_inputs())

    def enable(self, a):
        for cw, expected in ((6, 0x21), (7, 0x23), (15, 0x27)):
            status, *_ = self.cycle(a, cw)
            self.assertEqual(status & 0x6f, expected)
            self.assertTrue(status & 0x8000)

    def move(self, a, target, relative=False):
        expected = a.od.read(0x6064) + target if relative else target
        self.cycle(a, 15, target)
        status, *_ = self.cycle(a, 0x7f if relative else 0x3f, target)
        self.assertTrue(status & 0x1000)
        for count in range(2000):
            status, mode, position, velocity, torque, _ = self.cycle(a, 15, target)
            if status & 0x400 and position == expected: break
        else: self.fail('PP target not reached')
        self.assertEqual(mode, 1)
        self.assertEqual(velocity, 0)
        return count

    def test_absolute_relative_linear_rotary(self):
        for mode in ('linear', 'rotary'):
            with self.subTest(mode=mode):
                a = self.open(mode)
                self.enable(a)
                self.move(a, 2000)
                self.move(a, -750, relative=True)
                self.assertEqual(a.od.read(0x6064), 1250)

    def test_fault_reset_disable_and_independence(self):
        a, b = self.open(), self.open()
        self.enable(a); self.enable(b)
        self.move(a, 1000)
        self.assertEqual(b.od.read(0x6064), 0)
        a.inject_fault(True)
        status, *_ = self.cycle(a, 15)
        self.assertTrue(status & 8)
        self.assertTrue(status & 0x8000)
        self.assertFalse(b.od.read(0x6041) & 8)
        a.inject_fault(False)
        self.assertTrue(self.cycle(a, 15)[0] & 8)
        self.assertFalse(self.cycle(a, 0x80)[0] & 8)
        self.enable(a)
        self.assertEqual(self.cycle(a, 0)[0] & 0x6f, 0x40)

    def test_parameter_changes_affect_motion(self):
        fast, slow = self.open(), self.open()
        for a, velocity in ((fast, 10000), (slow, 1000)):
            a.write_sdo(0x6081, 0, round(velocity / a.velocity_factor).to_bytes(4, 'little'))
            for index in (0x6083, 0x6084):
                a.write_sdo(index, 0, round(50000 / a.acceleration_factor).to_bytes(4, 'little'))
            self.enable(a)
        self.assertGreater(self.move(slow, 2000), self.move(fast, 2000))

    def test_closed_instance_is_not_reused(self):
        a = self.open()
        a.close()
        with self.assertRaises(RuntimeError): a.step(.008)

    def test_mixed_fleet_persistence_and_model_identity(self):
        from functional_model.runtime.fleet import ModelFleet
        from functional_model.storage.parameter_store import ParameterStore
        from functional_model.configuration import load_environment
        import copy
        artifact = Path(os.environ['COPLEY_TEST_FMU']).resolve()
        with tempfile.TemporaryDirectory() as folder, ParameterStore(folder) as store:
            env = dict(KICKCAT_INTERFACE='enp1s0', DEVICE_SIMULATOR_STATE_DIR=folder,
                       DEVICE_SIMULATOR_FMU_DIR=str(artifact.parent),
                       DEVICE_SIMULATOR_BUS='0:axis:cia402-drive,1:axis:cia402-drive',
                       DEVICE_SIMULATOR_AXIS_IDS='0:copley0,1:internal1',
                       DEVICE_SIMULATOR_AXIS_MODELS='0:copley_drive_sim,1:f_kr_cmmt',
                       DEVICE_SIMULATOR_AXIS_MODES='0:linear,1:rotary',
                       DEVICE_SIMULATOR_AXIS_PARAMETER_SETS='0:copley0,1:internal1')
            config = load_environment(env)
            fleet = ModelFleet(config, store)
            self.addCleanup(fleet.close)
            m = fleet.models[0]
            m.dispatch(dict(op='write', index=0x6081, subindex=0, data=(1234).to_bytes(4,'little').hex()))
            m.dispatch(dict(op='write', index=0x2005, subindex=3, data='0100'))
            m.dispatch(dict(op='write', index=0x2005, subindex=1, data='01'))
            snapshot = store.path(m).read_bytes()
            self.assertNotIn(b'artifact', snapshot)
            self.assertEqual(len(m.parameter_values()), 8)
            self.enable(m.adapter)
            self.move(m.adapter, 1000)
            fleet.close()
            fresh = ModelFleet(config, store)
            self.addCleanup(fresh.close)
            a = fresh.models[0].adapter
            self.assertEqual(a.od.read(0x6081), 1234)
            self.assertEqual(a.od.read(0x6064), 0)
            self.assertTrue(a.od.read(0x6041) & 0x8000)
            a.step(.008)
            self.assertEqual(a.runner.get('ProfileVelocity'), 1234 * a.velocity_factor)
            fresh.generate_fixture(Path(folder) / 'fixture')
            self.assertEqual(len(fresh.describe()['devices']), 2)
            bad = copy.deepcopy(config)
            bad['devices'][0]['model'] = dict(type='f_kr_cmmt', mode='linear')
            with self.assertRaisesRegex(ValueError, 'incompatible'): ModelFleet(bad, store)
            self.assertEqual(store.path(m).read_bytes(), snapshot)

    def test_halt_does_not_stop_motion_or_fail_model(self):
        a = self.open()
        for cw in (0x106, 0x107, 0x10f): self.cycle(a, cw)
        self.assertEqual(a.od.read(0x6041) & 0x6f, 0x27)
        self.cycle(a, 0x13f, 2000)
        for _ in range(1000):
            status, _, position, velocity, _, _ = self.cycle(a, 0x10f, 2000)
            if position == 2000 and status & 0x400: break
        else: self.fail('Halt bit interrupted PP motion')
        self.assertEqual(a.od.read(0x6040), 0x10f)
        self.assertEqual(velocity, 0)
        a.inject_fault(True)
        self.assertTrue(self.cycle(a, 0x10f)[0] & 8)
        a.inject_fault(False)
        self.assertFalse(self.cycle(a, 0x180)[0] & 8)
