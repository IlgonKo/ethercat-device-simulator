"""Actual native FMUs vs frozen RF-015 Python, identical public OD commands.

Status/mode/target side effects must match each tick; feedback <= one raw LSB.
No reference-model internals are injected into the FMU.
"""
import math
import json
import os
from pathlib import Path
import unittest
from functional_model.cia402_drive.adapter.f_kr_cmmt import FKrCmmtAdapter
from tests.reference.f_kr_cmmt import FKrCmmtAdapter as Reference
from functional_model.cia402_drive.profile.profile import CiA402DriveProfile
from device_descriptions.cmmt_as.description import CmmtAsDescription


class FKrFmuTests(unittest.TestCase):
    stats = {}

    @classmethod
    def tearDownClass(cls):
        print('RF022_COMPARISON ' + json.dumps(cls.stats, sort_keys=True))
        if os.environ.get('RF022_REPORT'):
            Path(os.environ['RF022_REPORT']).write_text(json.dumps(cls.stats,indent=2)+'\n')

    def pair(self, mode):
        profile = CiA402DriveProfile(CmmtAsDescription(mode))
        a, b = Reference(profile), FKrCmmtAdapter(profile)
        self.addCleanup(b.close)
        self.axes = a, b
        self.variant = mode
        self.stats.setdefault(mode, dict(compared_ticks=0,max_raw_error=0,max_encoded_error=0,max_position_si_error=0,max_velocity_si_error=0))
        self.tick_number = 0
        return a, b

    def write(self, index, value, sub=0):
        for a in self.axes: a.od.write(index, value, sub)

    def tick(self, cw=None, n=1, dt=.008):
        if cw is not None: self.write(0x6040, cw)
        for _ in range(n):
            for a in self.axes: a.step(dt)
            self.tick_number += 1
            a,b=self.axes
            metrics=self.stats[self.variant];metrics['compared_ticks']+=1
            for i in (0x6041,0x6061):
                self.assertEqual(a.od.read(i),b.od.read(i),(self.tick_number,hex(i),a.od.read(i),b.od.read(i)))
            for i in (0x6064,0x606C,0x607A):
                error=abs(a.od.read(i)-b.od.read(i))
                metrics['max_raw_error']=max(metrics['max_raw_error'],error)
                self.assertLessEqual(error,1,(self.tick_number,hex(i),a.od.read(i),b.od.read(i)))
                encoded=abs(int.from_bytes(a.read_sdo(i,0,4),'little',signed=True)-int.from_bytes(b.read_sdo(i,0,4),'little',signed=True))
                metrics['max_encoded_error']=max(metrics['max_encoded_error'],encoded)
                self.assertLessEqual(encoded,1)
            for name,reference in [('position',a.model.actual_position),('velocity',a.model.actual_velocity)]:
                physical=abs(reference*b.angular_scale-b.runner.get('actual_'+name))
                key='max_'+name+'_si_error';metrics[key]=max(metrics[key],physical)

    def home(self):
        self.write(0x6060,6)
        for cw in (0,6,7,15):self.tick(cw)
        self.tick(0x1f,n=13)
        self.tick(15)
        self.assertTrue(self.axes[1].od.read(0x6041)&0x8000)

    def test_public_sequences(self):
        for mode in ('linear','rotary'):
            with self.subTest(mode=mode):
                self.pair(mode)
                self.write(0x6081,100);self.write(0x6083,1000);self.write(0x6084,1000)
                self.home()
                # PP frozen profile, ignored busy edge, next target, completion.
                self.write(0x6060,1);self.tick(15)
                self.write(0x607A,5000);self.tick(0x3f);self.tick(15,n=3)
                self.write(0x607A,8000);self.write(0x6081,50);self.write(0x6084,300)
                self.tick(0x3f,n=100);self.tick(15);self.tick(0x3f,n=150)
                self.write(0x607A,2147480000);self.tick(15);self.tick(0x3f)
                # PV and Jog: live acceleration, reversal, latched Stop, mode wait.
                for op in (3,-3):
                    self.tick(0);self.write(0x6060,op);self.write(0x60FF,0)
                    for cw in (6,7,15):self.tick(cw)
                    self.write(0x60FF,100);self.tick(0x101f if op==-3 else 15,n=25)
                    self.write(0x60FF,-100);self.tick(0x102f if op==-3 else 15,n=80)
                    self.write(0x6060,1);self.tick(n=5)
                    self.tick(0x10f,n=100);self.tick(15,n=10)
                # Quick Stop supersedes Halt, then requires fresh enable.
                self.tick(0);self.write(0x6060,3);self.write(0x60FF,0)
                for cw in (6,7,15):self.tick(cw)
                self.write(0x60FF,100);self.tick(n=25)
                self.write(0x6085,100);self.tick(0xb);self.write(0x6085,1000);self.tick(15,n=150)
                # Homing elapsed time, cancel and completed reference preservation.
                self.write(0x6060,6)
                for cw in (6,7,15):self.tick(cw)
                self.tick(0x1f,dt=.03,n=2);self.tick(15,n=20)
                self.tick(0x1f,dt=.03,n=3);self.tick(dt=.01)
                # CSP unchanged, rejected target OD side effect.
                self.write(0x6060,8);self.tick(15)
                self.write(0x607A,10000);self.tick(n=200)
                self.write(0x607A,2147480000);self.tick(n=5)
                self.tick(0x10f,n=50)
                for a in self.axes:a.deactivate()
                self.tick(n=5)

    def test_limits_and_rearm_both_variants(self):
        for mode in ('linear', 'rotary'):
            with self.subTest(mode=mode):
                self.pair(mode);self.home();self.write(0x6081,100)
                self.write(0x607D,1000,2);self.write(0x607D,-1000,1)
                self.write(0x6060,3);self.write(0x60FF,0);self.tick(15)
                self.write(0x60FF,100);self.tick(n=200)
                self.write(0x60FF,-100);self.tick(n=10)
                self.write(0x60FF,0);self.tick()
                self.write(0x60FF,-100);self.tick(n=200)
                self.write(0x60FF,0);self.tick()
                self.write(0x6060,1);self.tick(15)
                self.write(0x607A,1000);self.tick(0x3f,n=250)
                self.assertEqual(self.axes[1].od.read(0x6064),1000)

    def test_varied_steps_and_rotary_accumulation(self):
        for mode in ('linear','rotary'):
            with self.subTest(mode=mode):
                self.pair(mode);self.home();self.write(0x6081,100)
                limit=1000000000 if mode=='rotary' else 100000000
                target=200000000 if mode=='rotary' else 200000
                self.write(0x607D,limit,2);self.write(0x607D,-limit,1)
                self.write(0x6081,10000);self.write(0x607F,20000)
                self.write(0x2183,20,12);self.write(0x6083,100000);self.write(0x6084,100000)
                self.write(0x6060,1);self.tick(15)
                self.write(0x607A,target);self.tick(0x3f)
                for _ in range(250):
                    for dt in (.001,.007,.016,.03,.046):self.tick(dt=dt)
                self.assertEqual(self.axes[1].od.read(0x6064),target)

    def test_disable_does_not_replay_and_preserves_reference(self):
        self.pair('linear');self.home()
        self.write(0x6060,1);self.tick(15);self.write(0x607A,500000);self.tick(0x3f,n=20)
        for a in self.axes:a.deactivate()
        position=self.axes[1].od.read(0x6064)
        for cw in (0x16,0x17,0x1f):self.tick(cw)
        self.tick(n=20)
        self.assertEqual(self.axes[1].od.read(0x6064),position)
        self.assertTrue(self.axes[1].od.read(0x6041)&0x8000)
        self.tick(15);self.tick(0x3f)
        self.assertTrue(self.axes[1].od.read(0x6041)&0x100)

    def test_device_reset_and_save_od_response(self):
        self.pair('linear');self.home()
        self.write(0x6060,3);self.tick(15);self.write(0x60FF,100);self.tick(n=10)
        for a in self.axes:a.od.write_role('device_reset_command',1)
        self.tick()
        for a in self.axes:a.od.write_role('parameter_save_command',1)
        self.tick()
        for role in ('parameter_save_status','parameter_save_return_code','parameter_save_return_value'):
            self.assertEqual(self.axes[0].od.read_role(role),self.axes[1].od.read_role(role))

    def test_rehoming_completes_in_one_valid_step(self):
        self.pair('linear');self.home()
        self.write(0x607A,1234);self.tick(0x1f,dt=.1)
        self.assertEqual(self.axes[1].od.read(0x607A),0)
        self.write(0x607A,4321);self.tick(0x1f)
        self.assertEqual(self.axes[1].od.read(0x607A),4321)

    def test_bad_step_and_native_error_latch(self):
        _,a=self.pair('linear')
        with self.assertRaises(Exception):a.step(.101)
        self.assertTrue(a.runner.failed)
        with self.assertRaises(RuntimeError):a.step(.008)

    def test_instances_and_recreation(self):
        a,b=self.pair('linear')
        self.home();self.write(0x6060,3);self.tick(15)
        self.write(0x60FF,100);self.tick(n=20)
        other=FKrCmmtAdapter(CiA402DriveProfile(CmmtAsDescription('rotary')))
        self.addCleanup(other.close)
        other.step(.008)
        self.assertEqual(other.od.read(0x6064),0)
        self.assertEqual(other.od.read(0x6041)&0x804f,0x40)
        self.assertGreater(b.od.read(0x6064),0)
        b.close()
        fresh=FKrCmmtAdapter(CiA402DriveProfile(CmmtAsDescription('linear')))
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.runner.get('actual_position'),0)
        self.assertEqual(fresh.runner.get('status_word'),0x40)

    def test_standalone_invalid_physical_input_is_fmi_error(self):
        from functional_model.runtime.fmi.runner import Fmi3Runner
        artifact=Path(__file__).resolve().parents[2]/'model_artifacts/FKrCmmtLinear-linux.fmu'
        with Fmi3Runner(artifact,{}) as f:
            f.set('profile_acceleration',-1)
            with self.assertRaises(Exception):f.step(.008)
            self.assertTrue(f.failed)
            with self.assertRaises(RuntimeError):f.step(.008)

    def test_standalone_fmi_without_od_or_adapter(self):
        from pathlib import Path
        from functional_model.runtime.fmi.runner import Fmi3Runner
        root=Path(__file__).resolve().parents[2]/'model_artifacts'
        for variant in ('Linear','Rotary'):
            with Fmi3Runner(root/f'FKrCmmt{variant}-linux.fmu', {}) as f:
                self.assertEqual(f.get('status_word'),0x40)
                f.set('mode_request',3)
                for cw in (6,7,15):f.set('control_word',cw);f.step(.008)
                f.set('target_velocity',.1)
                for _ in range(20):f.step(.008)
                self.assertGreater(f.get('actual_position'),0)
                self.assertEqual(f.get('mode_display'),3)
                f.set('control_word',0);f.step(.008)
                self.assertEqual(f.get('actual_velocity'),0)

    def test_wrong_variant_rejected(self):
        from pathlib import Path
        artifact=Path(__file__).resolve().parents[2]/'model_artifacts/FKrCmmtRotary-linux.fmu'
        with self.assertRaisesRegex(ValueError,'dimension'):
            FKrCmmtAdapter(CiA402DriveProfile(CmmtAsDescription('linear')),artifact=artifact)

    def test_missing_artifact_is_not_python_fallback(self):
        with self.assertRaises(Exception):FKrCmmtAdapter(CiA402DriveProfile(CmmtAsDescription('linear')),artifact='/missing/fkr.fmu')

if __name__=='__main__':unittest.main()
