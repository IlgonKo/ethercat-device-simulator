import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('model_service',ROOT/'simulator/model_service.py')
service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)


class ModelServiceTests(unittest.TestCase):
    def setUp(self):
        model_root=os.environ.get('CMMT_MODEL_ROOT')
        if not model_root:self.skipTest('Set CMMT_MODEL_ROOT to run existing-model integration tests')
        self.model=service.Model(model_root)

    def test_default_contract_matches_existing_codec(self):
        spec=self.model.describe()
        self.assertEqual((spec['rx_size'],spec['tx_size']),(24,14))
        with tempfile.TemporaryDirectory() as d:
            service.generate_fixture(self.model,d)
            self.assertTrue((Path(d)/'cmmt.xml').is_file())

    def test_sdo_write_read_uses_same_od_as_pdo(self):
        self.model.dispatch(dict(op='write',index=0x6081,subindex=0,data=struct.pack('<I',123).hex()))
        self.assertEqual(self.model.servo.od.read(0x6081),123)
        self.assertEqual(self.model.dispatch(dict(op='read',index=0x6081,subindex=0))['data'],'7b000000')

    def test_write_length_rejected_before_mutation(self):
        old=self.model.servo.od.read(0x6081)
        with self.assertRaises(ValueError):self.model.dispatch(dict(op='write',index=0x6081,subindex=0,data='01'))
        self.assertEqual(self.model.servo.od.read(0x6081),old)

    def test_complete_access_communication_arrays_are_word_aligned(self):
        with tempfile.TemporaryDirectory() as d:
            service.generate_fixture(self.model,d)
            tree=ET.parse(Path(d)/'cmmt.xml')
            for index in (0x1c00,0x1c12,0x1c13,0x1600,0x1a00):
                dt=next(t for t in tree.findall('.//DataType') if t.findtext('Name')==f'SIM_{index:04X}')
                self.assertEqual(dt.findall('SubItem')[1].findtext('BitOffs'),'16')

    def test_readonly_write_is_not_accepted(self):
        from motion_server.failure import DeviceRejectedException
        with self.assertRaises(DeviceRejectedException):self.model.dispatch(dict(op='write',index=0x6041,subindex=0,data='0000'))
        self.assertEqual(self.model.servo.od.read(0x6041),0x40)

    def test_mailbox_does_not_tick_and_pdo_has_exact_length(self):
        self.model.dispatch(dict(op='read',index=0x6041,subindex=0))
        self.assertEqual(self.model.cycles,0)
        with self.assertRaises(ValueError):self.model.dispatch(dict(op='cycle',data='00'))
        self.assertEqual(self.model.cycles,0)

    def test_cia402_transitions_through_existing_model(self):
        with patch.object(service.time,'monotonic',side_effect=[10,10.01,10.02]):
            for cw,expected in [(6,0x21),(7,0x23),(15,0x27)]:
                payload=struct.pack('<HbiIihihB',cw,8,0,100,0,0,0,0,0)
                result=self.model.dispatch(dict(op='cycle',data=payload.hex()))
                self.assertEqual(int.from_bytes(bytes.fromhex(result['data'])[:2],'little')&0x6f,expected)
        self.assertEqual(self.model.cycles,3)

    def test_long_pdo_gap_fails_without_advancing_model(self):
        with patch.object(service.time,'monotonic',side_effect=[10,11]):
            self.model.dispatch(dict(op='cycle',data='00'*24))
            with self.assertRaises(RuntimeError):self.model.dispatch(dict(op='cycle',data='00'*24))
        self.assertEqual(self.model.cycles,1)

    def test_python_timing_preserves_pdo_response_and_splits_model_work(self):
        from simulator.python_timing import PythonTiming
        measured = service.Model(os.environ['CMMT_MODEL_ROOT'])
        measured.timing = PythonTiming(1)
        for n, cw in enumerate((6, 7, 15, 15)):
            request = dict(op='cycle', data=struct.pack('<HbiIihihB', cw, 3, 0, 100, 0, 0, 0, 0, 0).hex())
            with patch.object(service.time, 'monotonic', return_value=10+n*.01):
                expected = self.model.dispatch(request)
                actual = measured.dispatch(request)
            self.assertEqual(actual, expected)
        buckets = measured.timing.metrics
        for stage in ('rxpdo', 'model', 'txpdo', 'cycle_core'):
            self.assertEqual(buckets['axis_0_'+stage]['count'], 4)
        self.assertAlmostEqual(buckets['axis_0_cycle_core']['total_ms'],
            sum(buckets['axis_0_'+stage]['total_ms'] for stage in ('rxpdo', 'model', 'txpdo')), places=8)


if __name__=='__main__':unittest.main()
