import argparse,os,json,subprocess,time,signal,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('action',choices=['start','stop']);p.add_argument('run');p.add_argument('--mode',choices=['native','docker']);p.add_argument('--axes',type=int,choices=[2,4]);a=p.parse_args()
folder=BASE/a.run
if a.action=='start':
 folder.mkdir(mode=0o700);(folder/'state').mkdir()
 values=dict(KICKCAT_INTERFACE='enp1s0',DEVICE_SIMULATOR_STATE_DIR=str(folder/'state'),DEVICE_SIMULATOR_FMU_DIR=str(BASE),DEVICE_SIMULATOR_CYCLE_STATS_LOGS='1',DEVICE_SIMULATOR_SESSION_TIMEOUT='0',DEVICE_SIMULATOR_RUN_ID=a.run,DEVICE_SIMULATOR_BUS=','.join(f'{i}:axis:cia402-drive' for i in range(a.axes)))
 for k,vs in [('IDS',[f'bench-{i}' for i in range(a.axes)]),('MODELS',['f_kr_cmmt' if i%2==0 else 'copley_drive_sim' for i in range(a.axes)]),('MODES',['linear']*a.axes),('PARAMETER_SETS',[f'bench-{i}' for i in range(a.axes)])]:values['DEVICE_SIMULATOR_AXIS_'+k]=','.join(f'{i}:{v}' for i,v in enumerate(vs))
 (folder/'config.env').write_text('\n'.join(f'{k}={v}' for k,v in values.items()))
 if a.mode=='docker':
  subprocess.run(['docker','run','-d','--name','rf016-bench','--network=host','--read-only','--cap-drop=ALL','--cap-add=NET_RAW','--cap-add=NET_ADMIN','--cap-add=DAC_OVERRIDE','--security-opt=no-new-privileges:true','--tmpfs','/tmp:mode=1777','--tmpfs','/run/simulator:mode=0700','--tmpfs','/run/fmu:mode=0700,exec','-v',str(folder/'state')+':/state','--env-file',str(folder/'config.env'),'-e','DEVICE_SIMULATOR_STATE_DIR=/state','-e','DEVICE_SIMULATOR_FMU_DIR=/model_artifacts','-e','TMPDIR=/run/fmu','ethercat-device-simulator:rf014-verified'],check=True)
  for _ in range(100):
   log=subprocess.check_output(['docker','logs','rf016-bench'],stderr=subprocess.STDOUT,text=True)
   if 'CMMT_READY' in log:break
   time.sleep(.1)
  else:raise RuntimeError(log[-3000:])
  info={'mode':'docker'}
 else:
  socketdir=Path(tempfile.mkdtemp(prefix='rf016-'))
  socketpath=socketdir/'model.sock'
  env=dict(os.environ,PYTHONPATH=str(ROOT/'src')+':'+str(ROOT),DEVICE_SIMULATOR_STATE_DIR=str(folder/'state'),PYTHONUNBUFFERED='1')
  with (folder/'model.log').open('w') as log:
   model=subprocess.Popen([str(ROOT/'build/fmi-venv/bin/python'),'-m','functional_model','--env-file',str(folder/'config.env'),'--fixture-dir',str(folder/'fixture'),'--socket',str(socketpath),'--timing'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  for _ in range(100):
   if (socketpath).exists():break
   if model.poll() is not None:raise RuntimeError((folder/'model.log').read_text()[-2000:])
   time.sleep(.1)
  else:raise RuntimeError('No native model socket')
  with (folder/'slave.log').open('w') as log:
   slave=subprocess.Popen([str(ROOT/'build/timing/cmmt_simulator'),'enp1s0',str(folder/'fixture/cmmt.json'),str(folder/'fixture/contract.json'),str(socketpath),'--timing'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  for _ in range(100):
   if 'CMMT_READY' in (folder/'slave.log').read_text():break
   if slave.poll() is not None:
    model.terminate();raise RuntimeError((folder/'slave.log').read_text())
   time.sleep(.1)
  else:raise RuntimeError('No native ready')
  info={'mode':'native','pids':[slave.pid,model.pid]}
 (folder/'session.json').write_text(json.dumps(info));print('READY',a.run)
else:
 info=json.loads((folder/'session.json').read_text())
 if info['mode']=='docker':
  subprocess.run(['docker','stop','-t','10','rf016-bench'],check=True)
  log=subprocess.check_output(['docker','logs','rf016-bench'],stderr=subprocess.STDOUT)
  (folder/'combined.log').write_bytes(log);subprocess.run(['docker','rm','rf016-bench'],check=True)
 else:
  for pid in info['pids']:
   proc=Path('/proc')/str(pid)/'cmdline'
   if proc.exists() and str(folder).encode() in proc.read_bytes():os.kill(pid,signal.SIGTERM)
  time.sleep(.5)
 print('STOPPED',a.run)
