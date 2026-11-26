"""Build generated CPX fixtures, exercise the real KickCAT mailbox/ESC without a NIC."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import time
from functional_model.ipc.server import serve
from functional_model.configuration import load_environment, read_env
from functional_model.runtime.fleet import ModelFleet
from functional_model.storage.parameter_store import ParameterStore

ROOT=Path(__file__).resolve().parents[2]
class FixtureAdapter:
    """Test-only identity transfer; not the product analog-delay FMU."""
    def __init__(self,spec):pass
    def initial_outputs(self):return {'feedback':0}
    def step(self,inputs,t,dt):
        assert dt==.008
        return {'feedback':inputs['command']}
    def close(self):pass

def config_at(root, models=False):
    env=read_env(ROOT/'tests/fixtures/cpx-two-stations.env');env['DEVICE_SIMULATOR_STATE_DIR']=str(root/'state')
    config=load_environment(env,ROOT)
    if models:
        config['io_models']=[dict(id=i,preset=dict(schema_version=1,id=i,model='analog_delay',config={'delay_seconds':.016}),instance_config={}) for i in ['a','b']]
        for source,target,channel,ident in [(0,1,0,'a'),(1,0,1,'b')]:
            for station,kind,signal in [(source,'AO','command'),(target,'AI','feedback')]:
                config['devices'][station]['bindings'].append(dict(slot=3,kind=kind,channel=channel,instance=ident,signal=signal))
    return config

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',default=str(ROOT/'build/timing/test_remote_io'))
    parser.add_argument('--host');args=parser.parse_args()
    if args.host:
        root=Path(args.host);config=config_at(root,True)
        with ParameterStore(config['storage']['directory']) as store:
            fleet=ModelFleet(config,store,io_factory=FixtureAdapter)
            try:fleet.generate_fixture(root);serve(fleet,root/'model.sock')
            finally:fleet.close()
        return
    for models in (False,True):
        with tempfile.TemporaryDirectory(prefix='rf013-') as tmp:
            root=Path(tmp);config=config_at(root)
            child=None
            try:
                if models:
                    child=subprocess.Popen([sys.executable,__file__,'--host',tmp],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    for _ in range(100):
                        if (root/'model.sock').exists():break
                        if child.poll() is not None:raise RuntimeError(child.communicate()[0])
                        time.sleep(.02)
                    else:raise TimeoutError('IO model host startup')
                else:
                    with ParameterStore(config['storage']['directory']) as store:
                        fleet=ModelFleet(config,store)
                        try:fleet.generate_fixture(tmp)
                        finally:fleet.close()
                subprocess.run([args.binary,str(root/'cmmt.json'),str(root/'contract.json')]+([str(root/'model.sock')] if models else []),check=True)
                if child:
                    output,_=child.communicate(timeout=3)
                    if child.returncode:raise RuntimeError(output)
                assert not list((root/'state').glob('*.json')), 'CPX must not create axis parameter/mapping state'
            finally:
                if child and child.poll() is None:child.terminate();child.communicate(timeout=3)
if __name__=='__main__':main()
