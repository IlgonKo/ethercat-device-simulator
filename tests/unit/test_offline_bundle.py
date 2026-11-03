import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('offline', Path(__file__).resolve().parents[2] / 'scripts/deployment/offline.py')
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)


class OfflineBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'payload').write_bytes(b'valid')
        self.manifest = dict(schema=1, sha256={'payload':offline.digest(self.root/'payload')})
        self.save()

    def save(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))

    def test_valid_bundle(self):
        self.assertEqual(offline.verify(self.root),self.manifest)

    def test_corruption_is_rejected(self):
        (self.root/'payload').write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError,'Hash mismatch'): offline.verify(self.root)

    def test_missing_file_is_rejected(self):
        (self.root/'payload').unlink()
        with self.assertRaisesRegex(ValueError,'file list'): offline.verify(self.root)

    def test_unlisted_file_is_rejected(self):
        (self.root/'extra').write_text('unexpected')
        with self.assertRaisesRegex(ValueError,'file list'): offline.verify(self.root)

    def test_symlink_is_rejected(self):
        (self.root/'alias').symlink_to(self.root/'payload')
        with self.assertRaisesRegex(ValueError,'Symlink'): offline.verify(self.root)

    def test_outside_path_is_rejected(self):
        self.manifest['sha256']['../outside'] = 'a'*64
        self.save()
        with self.assertRaises(ValueError): offline.verify(self.root)

    def test_existing_work_directory_never_invokes_git(self):
        with patch.object(offline,'run') as run:
            with self.assertRaisesRegex(ValueError,'must not exist'):
                offline.restore_source(self.root,self.root,{})
            run.assert_not_called()

    def test_only_hash_matched_wheel_is_copied(self):
        wheels=self.root/'wheels';wheels.mkdir()
        good=wheels/'good.whl';good.write_bytes(b'wheel')
        (wheels/'other.whl').write_bytes(b'unexpected')
        req=self.root/'requirements.txt'
        req.write_text('pkg==1 --hash=sha256:'+offline.digest(good))
        target=self.root/'selected'
        offline.copy_locked_wheels(req,[wheels],target)
        self.assertEqual([f.name for f in target.iterdir()],['good.whl'])
        req.write_text('pkg==1 --hash=sha256:'+'0'*64)
        with self.assertRaisesRegex(ValueError,'Missing'):offline.copy_locked_wheels(req,[wheels],target)
