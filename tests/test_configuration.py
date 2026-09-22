import copy
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from simulator.configuration import load_config
from simulator.model_service import ModelFleet
from simulator.parameter_store import ParameterStore

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config.json'
        self.data = json.loads((ROOT/'config/four-axes.json').read_text())
        self.data['storage']['directory'] = 'parameters'

    def load(self, data=None):
        self.path.write_text(json.dumps(self.data if data is None else data))
        return load_config(self.path)

    def test_order_and_relative_storage(self):
        self.data['devices'].reverse()
        config = self.load()
        self.assertEqual([d['slave_index'] for d in config['devices']], [0, 1, 2, 3])
        self.assertEqual(config['storage']['directory'], str(self.path.parent/'parameters'))

    def test_reject_invalid_indices_ids_types_and_unknown_fields(self):
        for key, value in [('slave_index', True), ('slave_index', -1), ('slave_index', 1),
                           ('slave_index', 5), ('id', 'virtual-axis-1'),
                           ('parameter_set', 'axis-1'), ('parameter_set', '../escape'),
                           ('type', 'cpx_ap_i_ec'), ('pdo', 'motion_server_default')]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.data)
                data['devices'][0][key] = value
                with self.assertRaises(ValueError): self.load(data)

    def test_strict_json_and_version(self):
        for text in ['{"schema_version":1,"schema_version":1}', '{"x":NaN}']:
            self.path.write_text(text)
            with self.assertRaises(ValueError): load_config(self.path)
        for version in [True, 1.0, 2]:
            self.data['schema_version'] = version
            with self.assertRaises(ValueError): self.load()


class FleetTests(ConfigurationTests):
    def setUp(self):
        super().setUp()
        self.model_root = os.environ.get('CMMT_MODEL_ROOT')
        if not self.model_root: self.skipTest('Set CMMT_MODEL_ROOT')
        self.config = self.load()
        self.store = ParameterStore(self.config['storage']['directory'])
        self.store.__enter__()
        self.addCleanup(self.store.__exit__, None, None, None)
        self.fleet = ModelFleet(self.model_root, self.config, self.store)

    def write(self, index, obj, sub, fmt, value):
        return self.fleet.dispatch(dict(op='write', slave_index=index, index=obj,
                                      subindex=sub, data=struct.pack(fmt, value).hex()))

    def test_four_distinct_models_od_and_pdo(self):
        self.assertEqual(len({id(m.servo.od) for m in self.fleet.models}), 4)
        self.assertEqual([m.preset for m in self.fleet.models],
                         ['linear_mm', 'linear_mm', 'rotary_deg', 'rotary_deg'])
        for i in range(4): self.write(i, 0x607D, 2, '<i', 1000+i)
        self.assertEqual([m.servo.od.read(0x607D, 2) for m in self.fleet.models], list(range(1000, 1004)))
        for i, cw in enumerate([6, 7, 15, 0]):
            # Each slave sees its own controlword and independent cycle counter.
            payload = struct.pack('<HbiIihihB', cw, 3, 0, 100, 0, 0, 0, 0, 0)
            self.fleet.dispatch(dict(op='cycle', slave_index=i, data=payload.hex()))
        self.assertEqual([m.servo.od.read(0x6040) for m in self.fleet.models], [6, 7, 15, 0])
        self.assertEqual([m.cycles for m in self.fleet.models], [1]*4)
        self.fleet.dispatch(dict(op='cycle', slave_index=2, data='00'*24))
        self.assertEqual([m.cycles for m in self.fleet.models], [1, 1, 2, 1])

    def test_unsaved_changes_discarded_saved_parameters_restored_not_state(self):
        self.write(0, 0x607D, 2, '<i', 777)
        fresh = ModelFleet(self.model_root, self.config, self.store)
        self.assertEqual(fresh.models[0].servo.od.read(0x607D, 2), 1000000)
        self.write(0, 0x2005, 3, '<H', 1)
        self.write(0, 0x2005, 1, '<B', 1)
        self.fleet.models[0].servo.actual_position = 99
        fresh = ModelFleet(self.model_root, self.config, self.store)
        self.assertEqual(fresh.models[0].servo.od.read(0x607D, 2), 777)
        self.assertEqual(fresh.models[0].servo.actual_position, 0)
        self.assertEqual(fresh.models[0].servo.actual_velocity, 0)
        self.assertEqual(fresh.models[0].servo.od.read(0x6041), 0x40)
        self.assertFalse(fresh.models[0].servo.homing_referenced)

    def test_index_reorder_keeps_parameter_space(self):
        self.write(0, 0x607D, 2, '<i', 777)
        self.store.save(self.fleet.models[0])
        cfg = copy.deepcopy(self.config)
        cfg['devices'][0], cfg['devices'][1] = cfg['devices'][1], cfg['devices'][0]
        for i, d in enumerate(cfg['devices']): d['slave_index'] = i
        fresh = ModelFleet(self.model_root, cfg, self.store)
        self.assertEqual(fresh.models[1].servo.od.read(0x607D, 2), 777)
        self.assertEqual(fresh.models[0].servo.od.read(0x607D, 2), 1000000)

    def test_incompatible_mode_rejected_without_overwrite(self):
        path = self.store.path(self.fleet.models[0]); before = path.read_bytes()
        cfg = copy.deepcopy(self.config); cfg['devices'][0]['model']['mode'] = 'rotary'
        with self.assertRaisesRegex(ValueError, 'incompatible'): ModelFleet(self.model_root, cfg, self.store)
        self.assertEqual(path.read_bytes(), before)

    def test_corrupt_snapshot_and_missing_catalog_rejected(self):
        path = self.store.path(self.fleet.models[0]); path.write_text('{}')
        with self.assertRaises(ValueError): ModelFleet(self.model_root, self.config, self.store)
        self.assertEqual(path.read_text(), '{}')

    def test_atomic_save_failure_keeps_previous_snapshot(self):
        path = self.store.path(self.fleet.models[0]); before = path.read_bytes()
        self.write(0, 0x607D, 2, '<i', 777)
        self.write(0, 0x2005, 3, '<H', 1)
        with patch('simulator.parameter_store.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.write(0, 0x2005, 1, '<B', 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.fleet.models[0].servo.od.read(0x2005, 1), 0)

    def test_single_writer(self):
        with self.assertRaises(RuntimeError):
            with ParameterStore(self.store.root): pass

    def test_bad_slave_index_never_routes_to_axis_zero(self):
        for index in [True, -1, 4, '0', None]:
            with self.assertRaises(ValueError): self.fleet.dispatch(dict(op='idle', slave_index=index))

    def test_fleet_fixture_manifest(self):
        destination = self.path.parent/'fixtures'
        self.fleet.generate_fixture(destination)
        manifest = json.loads((destination/'cmmt.json').read_text())
        self.assertEqual(len(manifest['slaves']), 4)
        for path in manifest['slaves']: self.assertTrue(Path(path).is_file())
        self.assertEqual(json.loads((destination/'contract.json').read_text()), self.fleet.describe())

    def test_each_axis_moves_independently_in_existing_modes(self):
        for mode in (1, 3, 8, -3):
            fleet = ModelFleet(self.model_root, self.config, self.store)
            now = 10.0
            def tick(axis, cw, operation, target=0, velocity=0):
                nonlocal now
                now += .01
                payload = struct.pack('<HbiIihihB', cw, operation, target, 100, velocity, 0, 0, 0, 0)
                with patch('simulator.model_service.time.monotonic', return_value=now):
                    return fleet.dispatch(dict(op='cycle', slave_index=axis, data=payload.hex()))
            # Drive each selected model through Enable and its existing Homing path.
            for selected in range(4):
                for cw in (6, 7, 15): tick(selected, cw, 6)
                for _ in range(15): tick(selected, 31, 6)
                self.assertTrue(fleet.models[selected].servo.homing_referenced)
                before = [m.servo.actual_position for m in fleet.models]
                tick(selected, 15, mode, 10000, 100)
                for _ in range(40): tick(selected, 31 if mode in (1, -3) else 15, mode, 10000, 100)
                self.assertGreater(fleet.models[selected].servo.actual_position, before[selected], (mode, selected))
                for other in range(4):
                    if other != selected:
                        self.assertEqual(fleet.models[other].servo.actual_position, before[other])


if __name__ == '__main__': unittest.main()
