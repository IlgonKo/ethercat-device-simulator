"""Kill a real writer at persistence boundaries, using private stores only."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from functional_model.runtime.axis import Model
from functional_model.storage.parameter_store import ParameterStore


CHILD = r'''
import os, signal, sys
from functional_model.runtime.axis import Model
from functional_model.storage.parameter_store import ParameterStore
root, boundary = sys.argv[1:]
def stop():
    print('BOUNDARY', flush=True)
    os.kill(os.getpid(), signal.SIGSTOP)
with ParameterStore(root) as store:
    model = Model()
    store.load(model)
    model.adapter.od.write(0x6081, 222)
    real_replace, real_fsync = os.replace, os.fsync
    if boundary == 'partial':
        import functional_model.storage.parameter_store as module
        def partial_dump(data, stream, **kwargs):
            stream.write('{"schema_version":')
            stream.flush()
            stop()
        module.json.dump = partial_dump
    elif boundary == 'before_replace':
        def fsync(fd):
            real_fsync(fd)
            stop()
        os.fsync = fsync
    else:
        def replace(source, target):
            real_replace(source, target)
            stop()
        os.replace = replace
    store.save(model)
'''


@unittest.skipUnless(sys.platform == 'linux', 'SIGSTOP/SIGKILL boundary test requires Linux')
class ParameterCrashRecoveryTests(unittest.TestCase):
    def test_killed_writer_leaves_old_or_complete_new_snapshot_and_releases_lock(self):
        for boundary, expected in (('partial', 111), ('before_replace', 111), ('after_replace', 222)):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as root:
                model = Model()
                self.addCleanup(model.close)
                with ParameterStore(root) as store:
                    model.adapter.od.write(0x6081, 111)
                    store.save(model)
                    original = store.path(model).read_bytes()
                child = subprocess.Popen([sys.executable, '-c', CHILD, root, boundary],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    import select
                    self.assertTrue(select.select([child.stdout], [], [], 10)[0], 'Writer did not reach boundary')
                    self.assertEqual(child.stdout.readline().strip(), 'BOUNDARY')
                    child.kill()
                    child.communicate(timeout=5)
                    self.assertEqual(child.returncode, -signal.SIGKILL)
                    fresh = Model()
                    self.addCleanup(fresh.close)
                    with ParameterStore(root) as store:
                        self.assertTrue(store.load(fresh))
                        self.assertEqual(fresh.adapter.od.read(0x6081), expected)
                        if expected == 111:
                            self.assertEqual(store.path(fresh).read_bytes(), original)
                        # Orphan partial temp files must not be loaded as snapshots.
                        fresh.adapter.od.write(0x6081, 333)
                        store.save(fresh)
                        self.assertTrue(store.load(fresh))
                        self.assertEqual(fresh.adapter.od.read(0x6081), 333)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=5)

    def test_offline_backup_restore_and_explicit_reset(self):
        with tempfile.TemporaryDirectory() as root:
            model = Model()
            self.addCleanup(model.close)
            with ParameterStore(root) as store:
                model.adapter.od.write(0x6081, 111)
                store.save(model)
                target = store.path(model)
                original = target.read_bytes()
            backup = Path(root) / 'axis-0.json.backup'
            backup.write_bytes(original)
            with ParameterStore(root) as store:
                target.write_text('{broken', encoding='utf-8')
                with self.assertRaises(ValueError):
                    store.load(model)
                # Offline backup recovery: restore exact bytes, then strict load.
                staged = target.with_suffix('.restore')
                staged.write_bytes(backup.read_bytes())
                os.replace(staged, target)
                self.assertTrue(store.load(model))
                self.assertEqual(model.adapter.od.read(0x6081), 111)
                # Explicit reset preserves the previous snapshot instead of deleting it.
                target.rename(target.with_suffix('.before-reset'))
                fresh = Model()
                self.addCleanup(fresh.close)
                self.assertFalse(store.load(fresh))
                store.save(fresh)
                self.assertTrue(store.load(fresh))
                self.assertEqual(fresh.adapter.od.read(0x6081), 0)
                self.assertEqual(backup.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
