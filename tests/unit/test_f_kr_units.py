"""Physical/raw boundary and schema-3 persistence regression."""
import json
import tempfile
import unittest
from pathlib import Path
from functional_model.runtime.axis import Model
from functional_model.storage.parameter_store import ParameterStore
from functional_model.storage.migrate import migrate_quick_stop


class UnitBoundaryTests(unittest.TestCase):
    def model(self, mode="linear"):
        m = Model(dict(slave_index=0, id="test", type="cia402-drive",
                       model=dict(type="f_kr_cmmt", mode=mode)))
        self.addCleanup(m.close)
        return m

    def test_linear_od_to_physical_and_feedback_to_raw(self):
        m=self.model();a=m.adapter
        for index, sub, raw, physical in (
            (0x607A,0,100000,.1),(0x607D,1,-80000,-.08),
            (0x6081,0,100,.1),(0x6084,0,1000,1),
            (0x6085,0,2000,2),(0x2183,12,-.2,-.2)):
            a.od.write(index,raw,sub)
            self.assertAlmostEqual(a.units.read(index,sub),physical)
        a.model.actual_position=.012345
        a.model.actual_velocity=-.123
        a.model._write_actual_feedback()
        self.assertEqual(int.from_bytes(a.read_sdo(0x6064,0,4),'little',signed=True),12345)
        self.assertEqual(int.from_bytes(a.read_sdo(0x606C,0,4),'little',signed=True),-123)
        self.assertIs(a.od,a.model.od)

    def test_round_trip_preserves_raw_quantization_and_control_bits(self):
        a=self.model().adapter
        for index,sub in a.units.scales:
            values=(-12345,0,12345) if index not in (0x6067,0x6081,0x607F,0x6083,0x6084,0x6085) else (0,1,12345)
            for raw in values:
                a.od.write(index,raw,sub)
                a.units.write(index,a.units.read(index,sub),sub)
                self.assertAlmostEqual(a.od.read(index,sub),raw)
        a.od.write(0x6040,0x13f)
        self.assertEqual(a.units.read(0x6040),0x13f)
        a.units.write(0x6064,.0123457)
        self.assertEqual(int.from_bytes(a.read_sdo(0x6064,0,4),'little',signed=True),12345)

    def test_pv_physical_displacement_and_rotary_scaling(self):
        for mode in ("linear","rotary"):
            with self.subTest(mode=mode):
                a=self.model(mode).adapter
                a.od.write(0x6060,3);a.od.write(0x6083,1000);a.od.write(0x60FF,0)
                for cw in (6,7,15):
                    a.od.write(0x6040,cw);a.step(.008)
                a.od.write(0x60FF,100);a.step(.008)
                expected_v=a.units.scales[0x6083,0]*1000*.008
                expected_x=expected_v*.008
                self.assertAlmostEqual(a.model.actual_velocity,expected_v)
                self.assertAlmostEqual(a.model.actual_position,expected_x)
                self.assertAlmostEqual(a.od.read(0x6064),expected_x/a.units.scales[0x6064,0])


class QuickStopPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ParameterStore(self.temp.name).__enter__()
        self.addCleanup(self.store.__exit__,None,None,None)
        self.model=Model();self.addCleanup(self.model.close)

    def test_save_reload_and_invalid_configuration_rejection(self):
        self.model.adapter.write_sdo(0x6085,0,(2345).to_bytes(4,"little"))
        self.store.save(self.model)
        fresh=Model();self.addCleanup(fresh.close)
        self.assertTrue(self.store.load(fresh))
        self.assertEqual(fresh.adapter.od.read(0x6085),2345)
        self.assertEqual(fresh.adapter.od.read(0x605A),2)
        data=json.loads(self.store.path(fresh).read_text());data.pop("checksum")
        data["values"]["6085:00"]="00000000";data["checksum"]=self.store.checksum(data)
        self.store.path(fresh).write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"Quick Stop"):self.store.load(fresh)
        self.assertEqual(fresh.adapter.od.read(0x6085),2345)

    def test_old_schema_requires_explicit_offline_conversion(self):
        self.model.adapter.od.write(0x6084,3456)
        self.store.save(self.model);path=self.store.path(self.model)
        data=json.loads(path.read_text());data.pop("checksum")
        data["schema_version"]=2
        for key in ("605a:00","6085:00"):data["values"].pop(key)
        data["checksum"]=self.store.checksum(data)
        path.write_text(json.dumps(data));original=path.read_bytes()
        with self.assertRaisesRegex(ValueError,"incompatible"):self.store.load(self.model)
        self.assertEqual(path.read_bytes(),original)
        self.assertTrue(migrate_quick_stop(self.store,self.model))
        self.assertEqual(self.model.adapter.od.read(0x6085),3456)
        self.assertEqual(path.with_name(path.name+".schema2.bak").read_bytes(),original)
        self.assertFalse(migrate_quick_stop(self.store,self.model))
