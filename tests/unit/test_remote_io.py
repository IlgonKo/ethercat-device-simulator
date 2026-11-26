import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from functional_model.configuration import load_environment, validate_config
from functional_model.remote_io.configuration import models_from_environment, validate_bindings, validate_preset
from functional_model.remote_io.station import Station
from functional_model.remote_io.runtime import IORuntime

BASE={'KICKCAT_INTERFACE':'enp1s0','DEVICE_SIMULATOR_STATE_DIR':'state',
      'DEVICE_SIMULATOR_BUS':'0:io:cpx_ap_i_ec:io0,1:io:cpx_ap_i_ec:io1',
      'DEVICE_SIMULATOR_IO_io0_MODULES':'1:DI:8,2:DO:8,3:AIO:4:4,4:DO:8',
      'DEVICE_SIMULATOR_IO_io1_MODULES':'1:DO:8,2:DI:8,3:AIO:4:4'}
def cylinder(identifier='c'):
    return dict(id=identifier,preset=dict(schema_version=1,id='cylinder',model='pneumatic_double_acting',config={}),instance_config={})
def delay(identifier='a'):
    return dict(id=identifier,preset=dict(schema_version=1,id='delay',model='analog_delay',config={'delay_seconds':.016}),instance_config={})
def bind(station,slot,kind,channel,instance,signal):
    station['bindings'].append(dict(slot=slot,kind=kind,channel=channel,instance=instance,signal=signal))

class FixtureModel:
    """Test-only adapter. Not registered as a product behaviour model."""
    def __init__(self,spec):self.kind=spec['preset']['model'];self.calls=[];self.closed=False;self.enter=None;self.release=None;self.fail=False;self.invalid=False
    def initial_outputs(self):return {'extended':False,'retracted':True} if self.kind=='pneumatic_double_acting' else {'feedback':0}
    def step(self,inputs,t,dt):
        self.calls.append((dict(inputs),t,dt))
        if self.enter:self.enter.set();self.release.wait(1)
        if self.fail:raise RuntimeError('injected model failure')
        if self.kind=='analog_delay':return {'feedback':40000 if self.invalid else inputs['command']}
        return {'extended':inputs['extend'],'retracted':inputs['retract']}
    def close(self):self.closed=True

class RemoteIOTests(unittest.TestCase):
    def config(self):return load_environment(BASE,Path('/tmp'))
    def runtime(self,kind='cylinder',autostart=False,timeout=.1):
        cfg=self.config();d=cfg['devices'];spec=cylinder() if kind=='cylinder' else delay()
        if kind=='cylinder':
            bind(d[0],2,'DO',0,'c','extend');bind(d[1],1,'DO',1,'c','retract')
            bind(d[0],1,'DI',0,'c','extended');bind(d[1],2,'DI',1,'c','retracted')
        else:
            bind(d[0],3,'AO',0,'a','command');bind(d[1],3,'AI',0,'a','feedback')
        validate_bindings(d,[spec]);models={}
        def factory(s):models[s['id']]=FixtureModel(s);return models[s['id']]
        runtime=IORuntime([Station(x) for x in d],[spec],factory,timeout,autostart)
        self.addCleanup(runtime.close)
        return runtime,models[spec['id']]
    def snapshot(self,r,seq=1,active=(True,True),values=None):
        updates=[]
        for i,s in r.stations.items():
            entries=[]
            for e in s['station'].contract['entries']:
                if e.get('rx'):
                    v=(values or {}).get((i,e['index'],e['subindex']),0)
                    entries.append(dict(index=e['index'],subindex=e['subindex'],data=int(v).to_bytes((e['bits']+7)//8,'little',signed=e['bits']==16).hex()))
            updates.append(dict(slave_index=i,sequence=seq if type(seq)==int else seq[i],active=active[i],values=entries))
        return r.exchange(dict(session='test',request_id=seq,stations=updates))
    def test_profile_layout_and_offsets(self):
        station=Station(self.config()['devices'][0]);c=station.contract
        self.assertEqual((c['rx_size'],c['tx_size']),(11,9))
        self.assertEqual([sum(e['bits'] for e in p['entries']) for p in c['pdos'] if p['direction']=='rx'],[8,72,8])
        od={(e['index'],e['subindex']):e for e in c['entries']}
        self.assertEqual(od[0xf050,1]['initial'],'84200000')
        self.assertEqual(od[0xf050,4]['initial'],'34210000')
        self.assertTrue(all(e['access']=='ro' for k,e in od.items() if 0x1600<=k[0]<=0x1c13))
        self.assertNotIn((0x27f1,0),od);self.assertNotIn((0x10f3,0),od)
        self.assertEqual(len(c['channels']),32) # DI8 + DO8 + AIO8 + DO8, supply bits excluded
    def test_mixed_bus_axis_indices(self):
        env=dict(BASE);env.update(DEVICE_SIMULATOR_BUS=BASE['DEVICE_SIMULATOR_BUS']+',2:axis:cia402-drive',
            DEVICE_SIMULATOR_AXIS_IDS='2:axis2',DEVICE_SIMULATOR_AXIS_MODELS='2:f_kr_cmmt',DEVICE_SIMULATOR_AXIS_MODES='2:linear',DEVICE_SIMULATOR_AXIS_PARAMETER_SETS='2:p2')
        c=load_environment(env);self.assertEqual(c['devices'][2]['id'],'axis2')
    def test_invalid_module_and_unknown_settings(self):
        for modules in ['1:IOL:4','0:DI:8','2:DI:8','1:DI:8,1:DO:8','1:AIO:8:8']:
            with self.subTest(modules=modules),self.assertRaises(ValueError):load_environment(dict(BASE,DEVICE_SIMULATOR_IO_io0_MODULES=modules))
        with self.assertRaises(ValueError):load_environment(dict(BASE,DEVICE_SIMULATOR_IO_missing_MODULES='1:DI:8'))
    def test_binding_direction_and_global_uniqueness(self):
        c=self.config();d=c['devices'];bind(d[0],2,'DO',0,'c','extend');validate_bindings(d,[cylinder()])
        for b in [dict(d[0]['bindings'][0]),dict(slot=1,kind='DO',channel=0,instance='c',signal='extend')]:
            target=d[0] if b['slot']==2 else d[1];target['bindings'].append(b)
            with self.assertRaises(ValueError):validate_bindings(d,[cylinder()])
            target['bindings'].pop()
        bind(d[0],3,'AO',0,'c','retract')
        with self.assertRaises(ValueError):validate_bindings(d,[cylinder()])
    def test_preset_validation(self):
        for value in [-1,11,float('inf'),True]:
            p=delay()['preset'];p['config']['delay_seconds']=value
            with self.assertRaises(ValueError):validate_preset(p)
        p=delay()['preset'];p['config']={};validate_preset(p);self.assertEqual(p['config']['delay_seconds'],.016)
    def test_missing_required_input_waits_without_fault(self):
        for count in [0,1]:
            c=self.config();d=c['devices']
            if count:bind(d[0],2,'DO',0,'c','extend')
            with self.subTest(count=count):
                r=IORuntime([Station(x) for x in d],[cylinder()],FixtureModel,autostart=False);self.addCleanup(r.close)
                self.snapshot(r);self.assertFalse(r.step_once('c'));self.assertIsNone(r.instances['c']['fault'])
    def test_snapshot_and_fixed_dt(self):
        r,m=self.runtime();self.snapshot(r,values={(0,0x7020,1):1,(1,0x7010,2):1});r.step_once('c')
        self.assertEqual(m.calls[0],({'extend':True,'retract':True},0,.008))
        for n in range(2,20):self.snapshot(r,n)
        self.assertEqual(len(m.calls),1)
        r.step_once('c');self.assertEqual(m.calls[-1][1:],(.008,.008))
    def test_loss_requires_fresh_samples_from_all_input_stations(self):
        r,m=self.runtime();self.snapshot(r);r.step_once('c')
        self.snapshot(r,2,(False,True));self.assertFalse(r.step_once('c'))
        self.snapshot(r,(3,2));self.assertFalse(r.step_once('c'))
        self.snapshot(r,(3,3));self.assertTrue(r.step_once('c'));self.assertEqual(m.calls[-1][1],.008)
    def test_input_snapshot_does_not_change_during_step_and_final_step_is_kept(self):
        r,m=self.runtime();m.enter=threading.Event();m.release=threading.Event()
        self.snapshot(r,values={(0,0x7020,1):1})
        worker=threading.Thread(target=r.step_once,args=('c',));worker.start();self.assertTrue(m.enter.wait(.1))
        self.snapshot(r,2,(False,True));m.release.set();worker.join(.2)
        self.assertEqual(r.outputs[0][0x6010,1],'01');self.assertEqual(r.instances['c']['steps'],1)
        self.assertFalse(r.step_once('c'));self.assertTrue(m.calls[0][0]['extend'])
    def test_output_only_station_loss_does_not_pause_model(self):
        r,m=self.runtime('delay');self.snapshot(r,1,(True,False),{(0,0x7030,1):-32768});r.step_once('a')
        self.assertEqual(r.outputs[1][0x6030,1],'0080');self.assertEqual(len(m.calls),1)
    def test_timeout_latches_and_discards_late_output(self):
        r,m=self.runtime(timeout=.01);m.enter=threading.Event();m.release=threading.Event()
        self.snapshot(r,values={(0,0x7020,1):1});worker=threading.Thread(target=r.step_once,args=('c',));worker.start();m.enter.wait(.1)
        time.sleep(.015);response=self.snapshot(r,2);self.assertTrue(response['host_failed']);m.release.set();worker.join(.2)
        self.assertEqual(r.outputs[0][0x6010,1],'00');self.assertFalse(r.step_once('c'))
    def test_invalid_output_freezes_model(self):
        r,m=self.runtime('delay');self.snapshot(r,values={(0,0x7030,1):123});r.step_once('a');m.invalid=True
        r.step_once('a');self.assertEqual(r.outputs[1][0x6030,1],'7b00');self.assertIsNotNone(r.instances['a']['fault'])
        self.assertFalse(r.step_once('a'));self.assertFalse(r.host_failed)
        self.assertTrue(all(e['initial']==('00'*((e['bits']+7)//8)) for s in r.stations.values() for e in s['station'].contract['entries'] if e['index'] in (0x1001,0x6102) and e['subindex']!=0))
    def test_analog_boundaries_without_clamp(self):
        r,m=self.runtime('delay')
        for seq,v in enumerate([-32768,-1,0,1,32767],1):
            self.snapshot(r,seq,values={(0,0x7030,1):v});r.step_once('a')
            self.assertEqual(int.from_bytes(bytes.fromhex(r.outputs[1][0x6030,1]),'little',signed=True),v)
    def test_independent_instances_and_failure_isolation(self):
        c=self.config();d=c['devices'];specs=[delay('a'),delay('b')]
        for n,ident in enumerate(['a','b']):bind(d[0],3,'AO',n,ident,'command');bind(d[1],3,'AI',n,ident,'feedback')
        models={}
        def factory(s):models[s['id']]=FixtureModel(s);return models[s['id']]
        r=IORuntime([Station(x) for x in d],specs,factory,autostart=False);self.addCleanup(r.close)
        self.snapshot(r,values={(0,0x7030,1):100,(0,0x7030,2):200});models['a'].fail=True
        r.step_once('a');r.step_once('b');self.assertEqual(r.outputs[1][0x6030,2],'c800');self.assertFalse(r.host_failed)
    def test_runtime_closes_workers(self):
        r,m=self.runtime(autostart=True);self.snapshot(r);time.sleep(.04);r.close()
        self.assertTrue(m.closed);self.assertTrue(all(not w.is_alive() for w in r.workers))
        self.assertTrue(all(call[2]==.008 for call in m.calls))

    def test_short_overrun_keeps_result_without_catchup(self):
        r,m=self.runtime('delay');self.snapshot(r,values={(0,0x7030,1):321})
        original=m.step
        def delayed(*args):time.sleep(.012);return original(*args)
        m.step=delayed;r.step_once('a')
        self.assertFalse(r.host_failed);self.assertEqual(r.instances['a']['late_steps'],1)
        self.assertEqual(r.outputs[1][0x6030,1],'4101');self.assertEqual(r.instances['a']['steps'],1)
        r.step_once('a');self.assertEqual(m.calls[-1][1],.008)
    def test_model_steps_never_overlap(self):
        r,m=self.runtime();m.enter=threading.Event();m.release=threading.Event();self.snapshot(r)
        worker=threading.Thread(target=r.step_once,args=('c',));worker.start();self.assertTrue(m.enter.wait(.1))
        self.assertFalse(r.step_once('c'));m.release.set();worker.join(.2);self.assertEqual(len(m.calls),1)
    def test_missing_fmu_fails_clearly(self):
        from unittest.mock import patch
        from functional_model.remote_io.runtime import create_adapter
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'DEVICE_SIMULATOR_FMU_DIR':tmp}):
            with self.assertRaisesRegex(FileNotFoundError,'IO FMU missing'):create_adapter(cylinder())
    def test_preset_lookup_and_instance_config(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=cylinder()['preset'];p['id']='one';(root/'one.json').write_text(json.dumps(p))
            env=dict(BASE,DEVICE_SIMULATOR_BEHAVIOUR_MODELS='c:one',DEVICE_SIMULATOR_MODEL_c_INSTANCE_CONFIG='supply_gauge_pressure:600000,initial_position:0')
            result=models_from_environment(env,self.config()['devices'],root)
            self.assertEqual(result[0]['instance_config']['supply_gauge_pressure'],600000)
            (root/'duplicate.json').write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError,'Duplicate preset'):models_from_environment(env,self.config()['devices'],root)
    def test_fixture_has_no_mapping_persistence_and_is_stable(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as tmp:
            s=Station(self.config()['devices'][0]);s.generate_fixture(tmp)
            root=ET.parse(Path(tmp)/'cmmt.xml').getroot()
            coe=root.find('.//Mailbox/CoE');self.assertEqual(coe.get('PdoConfig'),'false')
            self.assertEqual(coe.get('CompleteAccess'),'false')
            first=(Path(tmp)/'cmmt.xml').read_bytes();s.generate_fixture(tmp)
            self.assertEqual(first,(Path(tmp)/'cmmt.xml').read_bytes())
