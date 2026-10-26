import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('docker_service', ROOT / 'docker/service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class DockerServiceTests(unittest.TestCase):
    def test_env_rejects_invalid_operational_settings(self):
        for bad in ({'KICKCAT_INTERFACE': '../eth0'},
                    {'KICKCAT_INTERFACE': 'eth0', 'DEVICE_SIMULATOR_CYCLE_STATS_LOGS': 'maybe'},
                    {'KICKCAT_INTERFACE': 'eth0', 'DEVICE_SIMULATOR_SESSION_TIMEOUT': '-1'},
                    {'KICKCAT_INTERFACE': 'eth0', 'DEVICE_SIMULATOR_RUN_ID': '../old'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                service.settings(bad)

    def test_defaults_do_not_limit_runtime(self):
        nic, timing, timeout, run_id = service.settings({'KICKCAT_INTERFACE': 'eth0'})
        self.assertEqual((nic, timing, timeout), ('eth0', False, 0))
        self.assertTrue(run_id)

    def test_health_rejects_stale_dead_and_degraded_processes(self):
        with tempfile.TemporaryDirectory() as folder:
            status = Path(folder) / 'status.json'
            with patch.object(service, 'STATUS', status), patch.object(service.os, 'kill') as kill:
                record = dict(event='ready', time=time.time(), processes={'model': {'pid': 123}})
                status.write_text(json.dumps(record))
                self.assertEqual(service.healthcheck(), 0)
                kill.side_effect = ProcessLookupError()
                self.assertEqual(service.healthcheck(), 1)
                kill.side_effect = None
                record['time'] -= 20
                status.write_text(json.dumps(record))
                self.assertEqual(service.healthcheck(), 1)
                record.update(event='model-failed', time=time.time())
                status.write_text(json.dumps(record))
                self.assertEqual(service.healthcheck(), 1)


if __name__ == '__main__':
    unittest.main()
