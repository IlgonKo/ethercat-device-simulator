import os
from pathlib import Path
import sys
import unittest

from functional_model.models.f_kr_internal.od_role_index import install_role_index


class RoleIndexTests(unittest.TestCase):
    def setUp(self):
        from functional_model.profiles.cia402_drive.object_dictionary import VirtualOdModel
        self.od = VirtualOdModel()
        self.reference = VirtualOdModel()
        install_role_index(self.od)

    def define(self, index, role):
        for od in (self.od, self.reference):
            od.define(index, name='test', data_type='int32', bit_size=32, role=role)

    def assert_lookup_equal(self, role):
        try:
            expected = self.reference.definition_by_role(role)
        except KeyError as exc:
            with self.assertRaises(KeyError) as actual:
                self.od.definition_by_role(role)
            self.assertEqual(actual.exception.args, exc.args)
        else:
            self.assertEqual(self.od.definition_by_role(role), expected)

    def test_missing_duplicate_redefinition_and_overlay(self):
        self.assert_lookup_equal('target')
        self.define(1, 'target')
        self.assert_lookup_equal('target')
        self.define(2, 'target')
        self.assert_lookup_equal('target')
        self.define(1, 'mode')
        self.assert_lookup_equal('target')
        for od in (self.od, self.reference):
            od.overlay(2, role='mode', default=42)
        self.assert_lookup_equal('target')
        self.assert_lookup_equal('mode')
        for od in (self.od, self.reference):
            od.overlay(3, name='new', data_type='int32', bit_size=32, role='target')
        self.assert_lookup_equal('target')

    def test_current_values_and_independent_instances(self):
        self.define(1, 'target')
        self.od.write_role('target', 17)
        self.assertEqual(self.od.read_role('target'), 17)
        self.assertEqual(self.reference.read_role('target'), 0)
        self.od.write_internal(1, 23)
        self.assertEqual(self.od.read_role('target'), 23)
        install_role_index(self.reference)
        self.reference.overlay(1, role='other')
        self.assertEqual(self.od.read_role('target'), 23)
        self.assertEqual(self.reference.read_role('other'), 0)

    def test_repeated_lookup_never_scans_entries(self):
        class CountingDict(dict):
            scans = 0
            def values(self):
                self.scans += 1
                return super().values()
        self.define(1, 'target')
        self.od.entries = CountingDict(self.od.entries)
        self.od.definition_by_role('target')
        scans = self.od.entries.scans
        for value in range(100):
            self.od.write_role('target', value)
            self.assertEqual(self.od.read_role('target'), value)
        self.assertEqual(self.od.entries.scans, scans)
        self.od.overlay(1, name='changed')
        self.assertEqual(self.od.definition_by_role('target').name, 'changed')
        self.assertEqual(self.od.entries.scans, scans + 1)

    def test_failed_overlay_retains_original_definition(self):
        self.define(1, 'target')
        before = self.od.definition_by_role('target')
        with self.assertRaises(TypeError):
            self.od.overlay(1, invalid_field=True)
        self.assertEqual(self.od.definition_by_role('target'), before)


if __name__ == '__main__':
    unittest.main()
