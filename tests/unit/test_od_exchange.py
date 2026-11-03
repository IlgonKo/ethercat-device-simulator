import unittest
from functional_model.runtime.axis import Model

class ODExchangeTests(unittest.TestCase):
    def test_subset_retains_sdo_and_returns_addresses(self):
        m = Model()
        m.dispatch(dict(op='write', index=0x6081, subindex=0, data='64000000'))
        out = m.dispatch(dict(op='exchange', active=True, session='a', request_id=1,
            values=[dict(index=0x6040, subindex=0, data='0000')],
            reads=[dict(index=0x6081, subindex=0),dict(index=0x6041, subindex=0)]))
        self.assertEqual(out['values'][0]['data'], '64000000')
        self.assertEqual(out['request_id'], 1)
        self.assertNotIn('data', out)
        self.assertIs(m.adapter.od, m.adapter.model.od)

    def test_invalid_update_has_no_partial_side_effect(self):
        m = Model()
        before = m.adapter.read_sdo(0x6040, 0, 2)
        with self.assertRaises(ValueError):
            m.dispatch(dict(op='exchange', active=True, values=[
                dict(index=0x6040, subindex=0, data='0f00'),
                dict(index=0x6041, subindex=0, data='2700')]))
        self.assertEqual(m.adapter.read_sdo(0x6040, 0, 2), before)

    def test_inactive_rearms_start_edge(self):
        m = Model()
        m.dispatch(dict(op='exchange', active=True, values=[dict(index=0x6040,subindex=0,data='1f00')]))
        self.assertFalse(m.pp_armed)
        m.dispatch(dict(op='exchange', active=False))
        self.assertFalse(m.pp_armed)
        m.dispatch(dict(op='exchange', active=True, values=[dict(index=0x6040,subindex=0,data='0f00')]))
        self.assertTrue(m.pp_armed)

    def test_inactive_retains_target_parameter(self):
        m = Model()
        m.operation_active = True
        m.adapter.od.write_internal(0x607A, 1234)
        m.dispatch(dict(op='exchange', active=False))
        self.assertEqual(m.adapter.od.read(0x607A), 1234)
        self.assertFalse(m.adapter.model.pp_active)

    def test_inactive_model_failure_is_latched_not_raised(self):
        m = Model()
        m.operation_active = True
        def fail(): raise RuntimeError('deactivate failed')
        m.adapter.deactivate = fail
        result = m.dispatch(dict(op='exchange', active=False, reads=[dict(index=0x6041,subindex=0)]))
        self.assertTrue(result['restart_required'])
        self.assertTrue(int.from_bytes(bytes.fromhex(result['values'][0]['data']), 'little') & 8)

    def test_omitted_object_is_not_written(self):
        m = Model()
        from unittest.mock import patch
        with patch.object(m.adapter.od, 'write', wraps=m.adapter.od.write) as write:
            m.dispatch(dict(op='exchange', active=True,
                            values=[dict(index=0x6040, subindex=0, data='0000')]))
        self.assertFalse(any(call.args[0] == 0x6081 for call in write.call_args_list))

    def test_contract_contains_definitions_not_pdo_layout(self):
        description = Model().describe()
        for key in ('rx', 'tx', 'rx_size', 'tx_size', 'pdo', 'mapping'):
            self.assertNotIn(key, description)
