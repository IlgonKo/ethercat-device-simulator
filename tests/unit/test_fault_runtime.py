import struct
import unittest
from unittest.mock import patch

from functional_model.runtime.axis import Model
from functional_model.cia402_drive.adapter.errors import DeviceRejectedException


def pdo(cw, mode=1, target=1000):
    return dict(op='cycle', data=struct.pack('<HbiIihihB', cw, mode, target, 100, 0, 0, 0, 0, 0).hex())


def status(response):
    return int.from_bytes(bytes.fromhex(response['data'])[:2], 'little')


class FaultRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.model = Model()
        self.tick = 10

    def cycle(self, cw, **kwargs):
        self.tick += .008
        with patch('functional_model.runtime.axis.time.monotonic', return_value=self.tick):
            return self.model.dispatch(pdo(cw, **kwargs))

    def test_adapter_fault_requires_correction_reset_and_new_enable(self):
        self.model.adapter.model.homing_referenced = True
        for cw in (6, 7, 15): self.cycle(cw)
        r = self.cycle(0x3f, mode=99)
        self.assertEqual(status(r) & 0x6f, 8)
        occurrence = r['fault']['diagnostic_id']
        # Reset while the cause remains cannot clear the Fault.
        self.assertEqual(status(self.cycle(0xbf, mode=99)) & 0x6f, 8)
        self.assertEqual(self.model.fault_state.fault.value['diagnostic_id'], occurrence)
        self.cycle(0x3f)
        r = self.cycle(0xbf)  # original CW retains Enable and setpoint bits
        self.assertTrue(status(r) & 8)  # cleared only after reset-low verification
        self.assertFalse(status(self.cycle(0x3f)) & 4)
        self.assertFalse(status(self.cycle(15)) & 4)
        for cw in [6]*5 + [7]*5: r = self.cycle(cw)
        self.assertEqual(status(r) & 0x6f, 0x23)
        self.assertEqual(status(self.cycle(15)) & 0x6f, 0x27)
        self.assertTrue(status(self.cycle(0x3f)) & 0x1000)
        self.assertFalse(status(self.cycle(15)) & 0x1000)

    def test_unexpected_model_exception_latches_and_does_not_call_model_again(self):
        self.cycle(6)
        last = self.model.fault_state.last
        with patch.object(self.model.adapter, 'step', side_effect=RuntimeError('FMU failed')) as step:
            r = self.cycle(7)
            for cw in (15, 0x8f, 6, 7, 15): self.cycle(cw)
            self.assertEqual(step.call_count, 1)
        self.assertTrue(r['restart_required'])
        self.assertEqual(bytes.fromhex(r['data'])[2:], last[2:])
        sw = self.model.dispatch(dict(op='read', index=0x6041, subindex=0))
        self.assertEqual(int(sw['data'], 16) & 0x0800, 0x0800)
        self.assertIn('error', self.model.dispatch(dict(op='write', index=0x6081, subindex=0, data='01000000')))

    def test_other_axis_remains_independent(self):
        other = Model(dict(slave_index=1, id='axis-1', type='cia402-drive',
                           model=dict(type='f_kr_cmmt', mode='linear'), parameter_set='test-1'))
        self.cycle(15, mode=99)
        with patch('functional_model.runtime.axis.time.monotonic', return_value=10):
            r = other.dispatch(pdo(6))
        self.assertEqual(status(r) & 0x6f, 0x21)
        self.assertIsNone(other.fault_state.fault)

    def test_bad_output_is_not_published(self):
        original = self.model.fault_state.last
        with patch.object(self.model.adapter, 'read_inputs', return_value=b'bad'):
            r = self.cycle(6)
        self.assertTrue(r['restart_required'])
        self.assertEqual(bytes.fromhex(r['data'])[2:], original[2:])

    def test_readonly_sdo_is_not_axis_fault(self):
        with self.assertRaises(DeviceRejectedException):
            self.model.dispatch(dict(op='write', index=0x6041, subindex=0, data='0000'))
        self.assertIsNone(self.model.fault_state.fault)


if __name__ == '__main__': unittest.main()
