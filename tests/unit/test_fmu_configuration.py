import tempfile
import unittest
from pathlib import Path
from functional_model.configuration import read_env, load_environment

ROOT = Path(__file__).resolve().parents[2]


class FmuConfigurationTests(unittest.TestCase):
    def test_mixed_models_resolve_artifact_without_changing_internal_model(self):
        env = read_env(ROOT / 'tests/fixtures/four-axes.env')
        env['DEVICE_SIMULATOR_AXIS_MODELS'] = '0:copley_drive_sim,1:f_kr_cmmt,2:copley_drive_sim,3:f_kr_cmmt'
        env['DEVICE_SIMULATOR_FMU_DIR'] = './artifacts with spaces'
        with tempfile.TemporaryDirectory() as folder:
            config = load_environment(env, folder)
            self.assertEqual(config['devices'][0]['model']['artifact'],
                             str(Path(folder) / 'artifacts with spaces/CopleyDriveSim-linux.fmu'))
            self.assertEqual(config['devices'][1]['model'], dict(type='f_kr_cmmt', mode='linear'))
        env['DEVICE_SIMULATOR_FMU_DIR'] = ''
        with self.assertRaises(ValueError): load_environment(env)
