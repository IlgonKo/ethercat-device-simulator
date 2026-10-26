"""Exercise shell dispatch/failure behavior with a fake Docker CLI, never a NIC."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux bash entrypoints')
class DockerScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'
        shutil.copytree(Path(__file__).resolve().parents[1] / 'scripts/docker', self.root / 'scripts/docker')
        repository = Path(__file__).resolve().parents[1]
        (self.root / 'simulator').mkdir()
        shutil.copy2(repository / 'simulator/configuration.py', self.root / 'simulator/configuration.py')
        shutil.copy2(repository / '.env.example', self.root / '.env')
        self.bin = Path(self.temp.name) / 'bin'
        self.bin.mkdir()
        self.log = Path(self.temp.name) / 'calls.jsonl'
        fake = self.bin / 'docker'
        fake.write_text('''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['CALL_LOG'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
args=sys.argv[1:]
if os.environ.get('FAKE_BUSY') and 'ps' in args: print('running-container')
if os.environ.get('FAKE_FAIL') in args: sys.exit(9)
''')
        fake.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(self.bin)+os.pathsep+os.environ['PATH'], 'CALL_LOG': str(self.log)}

    def run_script(self, name, *args, **env):
        result = subprocess.run(['bash', str(self.root / 'scripts/docker' / name), *args],
                                cwd=self.temp.name, env={**self.env, **env}, capture_output=True, text=True)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, calls

    def test_start_build_from_other_directory(self):
        result, calls = self.run_script('start.sh', '--build')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 3)
        self.assertIn('build', calls[1])
        self.assertIn('--force-recreate', calls[2])
        self.assertIn('--wait', calls[2])
        for call in calls:
            self.assertIn(str(self.root / 'build/compose.env'), call)
            self.assertIn(str(self.root / 'compose.yaml'), call)

    def test_failed_build_does_not_start_or_stop(self):
        result, calls = self.run_script('start.sh', '--build', FAKE_FAIL='build')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('up' in call or 'stop' in call for call in calls))

    def test_multiline_env_is_normalized_without_modifying_source(self):
        path = self.root / '.env'
        original = path.read_text().replace('0: virtual-axis-0, ', '0: virtual-axis-0,\\\n    ')
        path.write_text(original)
        result, calls = self.run_script('status.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_text(), original)
        normalized = (self.root / 'build/compose.env').read_text()
        self.assertIn('DEVICE_SIMULATOR_AXIS_IDS="0: virtual-axis-0,', normalized)
        self.assertEqual(len([x for x in normalized.splitlines() if 'DEVICE_SIMULATOR_AXIS_IDS=' in x]), 1)

    def test_stop_removes_only_service_without_volumes(self):
        result, calls = self.run_script('stop.sh')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls[-2][-2:], ['stop', 'simulator'])
        self.assertEqual(calls[-1][-3:], ['rm', '-f', 'simulator'])

    def test_validate_refuses_live_service(self):
        result, calls = self.run_script('validate.sh', FAKE_BUSY='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('run' in call for call in calls))

    def test_invalid_arguments_and_missing_env_do_not_call_docker(self):
        result, calls = self.run_script('start.sh', '--unknown')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])
        (self.root / '.env').unlink()
        result, calls = self.run_script('start.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
