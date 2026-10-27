import unittest
from functional_model.ipc.server import dispatch_request
from functional_model.cia402_drive.adapter.errors import DeviceRejectedException
from tests.unit.test_copley_adapter import FakeRunner
from functional_model.cia402_drive.adapter.copley import CopleyAdapter
from functional_model.cia402_drive.profile.profile import CiA402DriveProfile
from device_descriptions.cmmt_as.description import CmmtAsDescription


class SdoErrorTests(unittest.TestCase):
    def test_restart_clear_only_and_readback(self):
        a = CopleyAdapter(CiA402DriveProfile(CmmtAsDescription('linear')), FakeRunner())
        a.write_sdo(0x2000, 1, b'\0')
        with self.assertRaises(DeviceRejectedException): a.write_sdo(0x2000, 1, b'\1')
        self.assertEqual(a.read_sdo(0x2000, 1, 1), b'\0')
        self.assertEqual(len(a.read_sdo(0x216e, 1, 2)), 2)

    def test_rejected_sdo_then_success_on_same_dispatcher(self):
        class Model:
            def dispatch(self, request):
                if request['op'] == 'write': raise DeviceRejectedException('unsupported')
                return {'data': '0100'}
        m = Model()
        error = dispatch_request(m, {'op': 'write'})
        self.assertEqual(error['error']['code'], 0x06010000)
        self.assertEqual(dispatch_request(m, {'op': 'read'}), {'data': '0100'})

    def test_cycle_failure_is_not_hidden_by_sdo_handler(self):
        class Model:
            def dispatch(self, request): raise ValueError('invalid PDO')
        with self.assertRaisesRegex(ValueError, 'invalid PDO'):
            dispatch_request(Model(), {'op': 'cycle'})
