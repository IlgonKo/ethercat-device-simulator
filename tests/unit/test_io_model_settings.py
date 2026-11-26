"""Public IO model configuration, grouping and strict error boundaries."""
from pathlib import Path
import tempfile
import unittest
from functional_model.configuration import load_environment, read_env

ROOT = Path(__file__).resolve().parents[2]

class IOModelSettingsTests(unittest.TestCase):
    def env(self):
        return read_env(ROOT / 'tests/fixtures/cpx-fmu.env')

    def models(self, env):
        return {m['id']: m for m in load_environment(env, ROOT)['io_models']}

    def test_multiple_groups_are_independent(self):
        env = self.env()
        env['DEVICE_SIMULATOR_IO_MODEL_INSTANCES'] = (
            'cylinder1: supply_gauge_pressure:5e5,initial_position:0.02,opposing_force:-2, '
            'cylinder0: supply_gauge_pressure:600000,initial_position:0')
        m = self.models(env)
        self.assertEqual(m['cylinder0']['instance_config'], dict(supply_gauge_pressure=600000,initial_position=0))
        self.assertEqual(m['cylinder1']['instance_config'], dict(supply_gauge_pressure=500000,initial_position=.02,opposing_force=-2))
        self.assertEqual(m['analog0']['instance_config'], {})
        self.assertIsNot(m['cylinder0']['instance_config'],m['cylinder1']['instance_config'])

    def test_omitted_settings_use_fmu_defaults(self):
        env = self.env();env.pop('DEVICE_SIMULATOR_IO_MODEL_INSTANCES')
        self.assertTrue(all(not m['instance_config'] for m in self.models(env).values()))
        env['DEVICE_SIMULATOR_IO_MODEL_INSTANCES'] = 'cylinder0: initial_position:0.01'
        m = self.models(env)
        self.assertEqual(m['cylinder0']['instance_config'], {'initial_position':.01})
        self.assertEqual(m['cylinder1']['instance_config'], {})

    def test_fixture_continuations_match_one_line(self):
        env = self.env()
        self.assertEqual(self.models(env), self.models(dict(env, DEVICE_SIMULATOR_IO_MODEL_INSTANCES=
            'cylinder0:supply_gauge_pressure:600000,initial_position:0,cylinder1:supply_gauge_pressure:600000,initial_position:0')))

    def test_bad_group_syntax_duplicate_groups_and_values_are_rejected(self):
        for raw in [
            'initial_position:0', 'cylinder0:', 'cylinder0:initial_position:0,initial_position:1',
            'cylinder0:initial_position:0,cylinder0:supply_gauge_pressure:600000',
            'cylinder0:initial_position:0 cylinder1:supply_gauge_pressure:600000',
            'cylinder0::0', 'cylinder0:initial_position:', 'cylinder0:initial_position:0,,',
            'cylinder0:initial_position:nan','cylinder0:supply_gauge_pressure:inf',
        ]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.models(dict(self.env(),DEVICE_SIMULATOR_IO_MODEL_INSTANCES=raw))

    def test_unknown_or_unsupported_instance_settings_are_rejected(self):
        for raw in ['missing:initial_position:0','analog0:initial_position:0',
                    'cylinder0:stroke:0.2','cylinder0:initial_position:0.101',
                    'cylinder0:supply_gauge_pressure:-1']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.models(dict(self.env(),DEVICE_SIMULATOR_IO_MODEL_INSTANCES=raw))

    def test_legacy_keys_are_rejected_even_when_empty(self):
        for key in ['DEVICE_SIMULATOR_BEHAVIOUR_MODELS','DEVICE_SIMULATOR_MODEL_cylinder0_INSTANCE_CONFIG']:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'Retired IO model settings'):
                self.models(dict(self.env(),**{key:''}))

    def test_duplicate_model_declarations_and_unknown_io_keys_are_rejected(self):
        for key,value in [('DEVICE_SIMULATOR_IO_MODELS','cylinder0:cylinder_100mm,cylinder0:cylinder_100mm'),
                          ('DEVICE_SIMULATOR_IO_MODEL_INSTNACES',''),
                          ('DEVICE_SIMULATOR_IO_io9_BINDINGS','')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.models(dict(self.env(),**{key:value}))
