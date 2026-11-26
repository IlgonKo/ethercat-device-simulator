"""Actual FMI 3.0 artifacts: IO_TEST_FMU_DIR must contain both IO FMUs."""
import copy
import os
from pathlib import Path
import tempfile
import time
import unittest
from functional_model.configuration import load_environment,read_env
from functional_model.remote_io.adapter.fmi import FmiIOAdapter,DELAY_SIGNATURE
from functional_model.remote_io.runtime import IORuntime
from functional_model.remote_io.station import Station
from functional_model.runtime.fmi.runner import Fmi3Runner

ROOT=Path(__file__).resolve().parents[2]

@unittest.skipUnless(os.environ.get('IO_TEST_FMU_DIR'),'IO_TEST_FMU_DIR is not set')
class IOFmuTests(unittest.TestCase):
    def adapter(self,kind='analog_delay',config=None,initial=None,identifier='test'):
        a=FmiIOAdapter(dict(id=identifier,preset=dict(model=kind,config=config or {}),instance_config=initial or {}),os.environ['IO_TEST_FMU_DIR'])
        self.addCleanup(a.close);return a
    def test_delay_step_timing_and_signed_sequence(self):
        for delay in [0,.008,.016,.020,.037,10]:
            a=self.adapter(config={'delay_seconds':delay},identifier='delay_'+str(delay))
            self.assertEqual(a.initial_outputs(),{'feedback':0})
            inputs=[-32768,-1,0,32767,123,-456]*220 if delay==10 else [-32768,-1,0,32767,123,-456]*6
            expected_first=None
            for n,value in enumerate(inputs):
                result=a.step({'command':value},n*.008,.008)['feedback']
                eligible=[j for j in range(n+1) if j*.008+delay<=(n+1)*.008+1e-10]
                expected=inputs[eligible[-1]] if eligible else 0
                self.assertEqual(result,expected,(delay,n))
                if expected_first is None and eligible:expected_first=(n+1)*.008
            if delay in (0,.016,.020):self.assertAlmostEqual(expected_first,{0:.008,.016:.016,.020:.024}[delay])
    def test_delay_native_reset_and_instance_isolation(self):
        a=self.adapter(config={'delay_seconds':.020},identifier='a');b=self.adapter(config={'delay_seconds':0},identifier='b')
        a.step({'command':32767},0,.008);self.assertEqual(b.step({'command':-32768},0,.008)['feedback'],-32768)
        a.step({'command':1},.008,.008);self.assertEqual(a.step({'command':2},.016,.008)['feedback'],32767)
        self.assertEqual(b.initial_outputs()['feedback'],-32768)
        a.close();fresh=self.adapter(config={'delay_seconds':.020});self.assertEqual(fresh.initial_outputs()['feedback'],0)
        self.assertEqual(fresh.step({'command':9},0,.008)['feedback'],0)
    def test_delay_contract_rejects_invalid_values_and_runtime_parameter_writes(self):
        a=self.adapter()
        for value in [-32769,32768,1.5,True]:
            with self.assertRaises(ValueError):a.runner.set('command',value)
        with self.assertRaisesRegex(ValueError,'initialization-only'):a.runner.set('delay_seconds',.1)
        for delay in [-1,11,float('nan')]:
            with self.assertRaises(ValueError):self.adapter(config={'delay_seconds':delay})
    def test_native_delay_fmi_reset_clears_buffer(self):
        a=self.adapter();a.step({'command':99},0,.008);a.step({'command':100},.008,.008)
        native=a.runner._fmu;native.reset();native.enterInitializationMode(startTime=0.);native.exitInitializationMode()
        a.runner.time=0
        self.assertEqual(a.initial_outputs()['feedback'],0)
        self.assertEqual(a.step({'command':0},0,.008)['feedback'],0)
    def test_cylinder_initial_settings_and_motion(self):
        for stroke in [.05,.1]:
            a=self.adapter('pneumatic_double_acting',{'stroke':stroke},identifier='stroke_'+str(stroke))
            self.assertEqual(a.initial_outputs(),dict(extended=False,retracted=True))
            self.assertAlmostEqual(a.runner.get('stroke'),stroke)
            for n in range(150):a.step(dict(extend=n<15,retract=False),n*.008,.008)
            self.assertTrue(a.initial_outputs()['extended']);self.assertAlmostEqual(a.runner.get('position'),stroke,delta=.002)
            # Both commands off retain valve direction and position near extended end.
            self.assertTrue(a.runner.get('valve_extended'))
            for n in range(150,300):a.step(dict(extend=False,retract=n<165),n*.008,.008)
            self.assertTrue(a.initial_outputs()['retracted']);self.assertAlmostEqual(a.runner.get('position'),0,delta=.002)
    def test_cylinder_initial_position_zero_pressure_and_dual_command(self):
        a=self.adapter('pneumatic_double_acting',{'stroke':.05},dict(initial_position=.025,supply_gauge_pressure=0))
        self.assertAlmostEqual(a.runner.get('position'),.025,places=6)
        self.assertEqual(a.initial_outputs(),dict(extended=False,retracted=False))
        for n in range(50):a.step(dict(extend=True,retract=True),n*.008,.008)
        self.assertTrue(a.runner.get('extend_command'));self.assertTrue(a.runner.get('retract_command'))
        self.assertAlmostEqual(a.runner.get('position'),.025,delta=.001)
    def runtime(self,autostart=False):
        settings=read_env(ROOT/'tests/fixtures/cpx-fmu.env');settings['DEVICE_SIMULATOR_FMU_DIR']=os.environ['IO_TEST_FMU_DIR']
        config=load_environment(settings,ROOT)
        r=IORuntime([Station(d) for d in config['devices']],config['io_models'],autostart=autostart)
        self.addCleanup(r.close);return r
    def update(self,r,sequence,active=(True,True),values=None):
        stations=[]
        for i,state in r.stations.items():
            entries=[]
            for e in state['station'].contract['entries']:
                if not e.get('rx'):continue
                value=(values or {}).get((i,e['index'],e['subindex']),0)
                entries.append(dict(index=e['index'],subindex=e['subindex'],data=int(value).to_bytes((e['bits']+7)//8,'little',signed=e['bits']==16).hex()))
            stations.append(dict(slave_index=i,sequence=sequence if type(sequence)==int else sequence[i],active=active[i],values=entries))
        return r.exchange(dict(session='fmu-test',request_id=sequence,stations=stations))
    def test_four_real_fmus_cross_station_pipeline_and_pause(self):
        r=self.runtime();self.assertEqual(r.outputs[1][0x6010,1],'01') # cylinder0 initially retracted
        for n in range(150):
            self.update(r,n+1,values={(0,0x7020,1):n<15,(1,0x7020,2):n<15,(0,0x7030,1):-32768,(1,0x7030,2):32767})
            for ident in r.instances:r.step_once(ident)
        self.assertEqual(r.outputs[0][0x6010,1],'01');self.assertEqual(r.outputs[1][0x6010,2],'01')
        self.assertEqual(r.outputs[1][0x6030,1],'0080');self.assertEqual(r.outputs[0][0x6030,2],'ff7f')
        before={k:(m['steps'],m['adapter'].runner.time) for k,m in r.instances.items()}
        self.update(r,151,(False,True))
        # Cylinders depend on both stations; analog1 only on station1 (output on station0).
        for k in ['cylinder0','cylinder1','analog0']:self.assertFalse(r.step_once(k))
        self.assertTrue(r.step_once('analog1'))
        self.update(r,(152,151));self.assertFalse(r.step_once('cylinder0'))
        self.update(r,(152,152));self.assertTrue(r.step_once('cylinder0'))
        self.assertEqual(r.instances['cylinder0']['steps'],before['cylinder0'][0]+1)
        self.assertAlmostEqual(r.instances['cylinder0']['adapter'].runner.time,before['cylinder0'][1]+.008)
        self.assertFalse(r.host_failed);self.assertTrue(all(m['fault'] is None for m in r.instances.values()))
    def test_actual_delay_preserves_pending_history_during_pause(self):
        r=self.runtime();self.update(r,1,values={(0,0x7030,1):123});r.step_once('analog0')
        self.assertEqual(r.outputs[1][0x6030,1],'0000');self.update(r,2,(False,True))
        for _ in range(20):self.assertFalse(r.step_once('analog0'))
        self.update(r,3,values={(0,0x7030,1):456});r.step_once('analog0')
        self.assertEqual(r.outputs[1][0x6030,1],'7b00')
    def test_actual_native_calls_on_scheduler_workers(self):
        r=self.runtime(autostart=True);self.update(r,1,values={(0,0x7030,1):77,(1,0x7030,2):-88})
        time.sleep(.1);r.close()
        self.assertFalse(r.host_failed)
        self.assertTrue(all(m['steps']>=2 and m['fault'] is None for m in r.instances.values()))
        self.assertTrue(all(not w.is_alive() for w in r.workers))
        self.assertEqual(r.outputs[1][0x6030,1],'4d00');self.assertEqual(r.outputs[0][0x6030,2],'a8ff')
    def test_missing_cylinder_input_keeps_fmu_initialized_without_time_progression(self):
        env=read_env(ROOT/'tests/fixtures/cpx-fmu.env');env['DEVICE_SIMULATOR_FMU_DIR']=os.environ['IO_TEST_FMU_DIR']
        c=load_environment(env,ROOT)
        for d in c['devices']:d['bindings']=[b for b in d['bindings'] if not (b['instance']=='cylinder0' and b['signal']=='retract')]
        r=IORuntime([Station(d) for d in c['devices']],c['io_models'],autostart=False);self.addCleanup(r.close)
        self.update(r,1)
        self.assertFalse(r.step_once('cylinder0'));self.assertEqual(r.instances['cylinder0']['adapter'].runner.time,0)
