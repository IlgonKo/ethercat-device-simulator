import json
import tempfile
import unittest
from unittest.mock import patch

from functional_model.runtime.axis import Model
from functional_model.storage.parameter_store import ParameterStore
from functional_model.storage.migrate import migrate_profile_velocity


class ParameterMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ParameterStore(self.temp.name).__enter__()
        self.addCleanup(self.store.__exit__, None, None, None)
        self.model = Model()
        self.addCleanup(self.model.close)
        self.model.store = self.store
        self.model.adapter.od.write(0x6083, 2345)
        self.store.save(self.model)
        self.path = self.store.path(self.model)
        data = json.loads(self.path.read_text())
        data.pop('checksum')
        data['schema_version'] = 1
        data['values'].pop('6081:00')
        data['checksum'] = self.store.checksum(data)
        self.path.write_text(json.dumps(data))
        self.original = self.path.read_bytes()

    def test_explicit_migration_preserves_values_backup_and_is_idempotent(self):
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            self.store.load(self.model)
        self.assertTrue(migrate_profile_velocity(self.store, self.model, 1234))
        fresh = Model()
        self.addCleanup(fresh.close)
        self.assertTrue(self.store.load(fresh))
        self.assertEqual(fresh.adapter.od.read(0x6081), 1234)
        self.assertEqual(fresh.adapter.od.read(0x6083), 2345)
        self.assertEqual(fresh.adapter.od.read(0x6064), 0)
        self.assertFalse(fresh.adapter.od.read(0x6041) & 4)
        self.assertEqual(self.path.with_name(self.path.name+'.schema1.bak').read_bytes(), self.original)
        self.assertFalse(migrate_profile_velocity(self.store, fresh, 9999))
        self.assertEqual(fresh.adapter.od.read(0x6081), 1234)

    def test_write_failure_preserves_original(self):
        with patch('functional_model.storage.parameter_store.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                migrate_profile_velocity(self.store, self.model, 1234)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_corrupt_snapshot_and_invalid_velocity_do_not_modify_file(self):
        for velocity in (-1, 2**32, True):
            with self.assertRaises(ValueError):
                migrate_profile_velocity(self.store, self.model, velocity)
        data = json.loads(self.path.read_text())
        data['values'].pop('6083:00')
        data.pop('checksum')
        data['checksum'] = self.store.checksum(data)
        self.path.write_text(json.dumps(data))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'catalog'):
            migrate_profile_velocity(self.store, self.model, 1234)
        self.assertEqual(self.path.read_bytes(), before)

    def test_sdo_save_restores_velocity_but_discards_unsaved_change(self):
        migrate_profile_velocity(self.store, self.model, 1234)
        for index, sub, payload in ((0x6081, 0, (4321).to_bytes(4, 'little').hex()),
                                    (0x2005, 3, '0100'), (0x2005, 1, '01')):
            self.model.dispatch(dict(op='write', index=index, subindex=sub, data=payload))
        self.model.adapter.od.write(0x6081, 9999)
        fresh = Model()
        self.addCleanup(fresh.close)
        self.store.load(fresh)
        self.assertEqual(fresh.adapter.od.read(0x6081), 4321)


if __name__ == '__main__':
    unittest.main()
