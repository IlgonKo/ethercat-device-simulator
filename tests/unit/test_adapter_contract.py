from types import SimpleNamespace
import struct
import unittest
from functional_model.adapters.contract import validate_adapter
from functional_model.adapters.registry import create_adapter
from functional_model.adapters.errors import DeviceRejectedException
from functional_model.runtime.axis import Model

class AdapterContractTests(unittest.TestCase):
    def test_minimal_adapter_has_no_model_or_bridge_requirement(self):
        adapter = SimpleNamespace(profile=object(), od=object(), capabilities=object(),
            read_sdo=lambda *args: b'', write_sdo=lambda *args: None,
            apply_outputs=lambda payload: None, step=lambda dt: None, read_inputs=lambda: b'')
        self.assertIs(validate_adapter(adapter), adapter)
        del adapter.step
        with self.assertRaisesRegex(TypeError, 'requires step'): validate_adapter(adapter)

    def test_unknown_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported profile/model'):
            create_adapter(dict(type='cmmt-as', model=dict(type='unknown', mode='linear')))

    def test_unsupported_mode_never_mutates_od(self):
        model = Model()
        adapter = model.adapter
        before = adapter.read_sdo(0x6060, 0, 1)
        with self.assertRaises(DeviceRejectedException): adapter.write_sdo(0x6060, 0, b'\x04')
        self.assertEqual(adapter.read_sdo(0x6060, 0, 1), before)
        controlword = adapter.read_sdo(0x6040, 0, 2)
        payload = struct.pack('<HbiIihihB', 15, 4, 100, 100, 0, 0, 0, 0, 0)
        with self.assertRaises(DeviceRejectedException): adapter.apply_outputs(payload)
        self.assertEqual(adapter.read_sdo(0x6040, 0, 2), controlword)

    def test_shared_definition_has_independent_state(self):
        first, second = Model(), Model()
        self.assertEqual(first.profile.name, 'cia402-drive')
        self.assertIsNot(first.adapter.od, second.adapter.od)
        self.assertEqual(first.adapter.capabilities.state_machine_owner, 'model')
        self.assertIs(first.adapter.model.od, first.adapter.od)
        first.adapter.write_sdo(0x6081, 0, (99).to_bytes(4,'little'))
        self.assertNotEqual(first.adapter.read_sdo(0x6081,0,4), second.adapter.read_sdo(0x6081,0,4))
