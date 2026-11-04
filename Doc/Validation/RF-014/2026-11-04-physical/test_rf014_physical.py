import pysoem,json,time,threading,struct,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NIC=r'\Device\NPF_{906A65C9-C606-4B1F-8384-2625829A4D18}'
RX=[8,0x60400010]
TX=[0x60640020,0x60410010,0x60610008,0x606c0020,8]
def check(ok,text):
 if not ok:raise AssertionError(text)
def mapping(s,rx,tx):
 for assign,pdo,items in [(0x1c12,0x1600,rx),(0x1c13,0x1a00,tx)]:
  s.sdo_write(assign,0,b'\0');s.sdo_write(pdo,0,b'\0')
  for sub,word in enumerate(items,1):s.sdo_write(pdo,sub,word.to_bytes(4,'little'))
  s.sdo_write(pdo,0,bytes([len(items)]));s.sdo_write(assign,1,pdo.to_bytes(2,'little'));s.sdo_write(assign,0,b'\1')
def readmap(s,index):
 n=int.from_bytes(s.sdo_read(index,0),'little');return [int.from_bytes(s.sdo_read(index,j),'little') for j in range(1,n+1)]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['exercise','verify_restore','restore_default']);args=parser.parse_args()
 result=dict(stage=args.stage,started=time.time(),aborts=[]);m=pysoem.Master();m.open(NIC);lock=threading.Lock();stop=threading.Event();worker=None
 cw=[0]*4; samples=[]; wkc=[];errors=[]; measuring=False
 def read(s,index,sub=0):
  with lock:return s.sdo_read(index,sub)
 def write(s,index,data,sub=0):
  with lock:s.sdo_write(index,sub,data)
 def abort(name,fn,expected):
  try:fn()
  except pysoem.SdoError as e:
   result['aborts'].append(dict(name=name,code=hex(e.abort_code)));check(e.abort_code==expected,f'{name}: {e.abort_code:#x}')
  else:raise AssertionError(name+' did not abort')
 def cycle():
  next_due=time.perf_counter()
  try:
   while not stop.is_set():
    with lock:
     for i,s in enumerate(m.slaves):s.output=(bytes([0])+struct.pack('<H',cw[i-2])) if i>=2 else bytes(len(s.output))
     m.send_processdata();got=m.receive_processdata(3000)
     if measuring:
      wkc.append(got);samples.append([struct.unpack('<iHbiB',s.input) for s in m.slaves[2:]])
    next_due+=.008;time.sleep(max(0,next_due-time.perf_counter()))
  except Exception as e:errors.append(repr(e));stop.set()
 try:
  check(m.config_init()==6,'Expected six slaves')
  check(all(s.man==29 and s.id==8067733 and s.rev==36120 for s in m.slaves[2:]),'Virtual identities mismatch')
  m.state=pysoem.PREOP_STATE;m.write_state();check(m.state_check(pysoem.PREOP_STATE,2_000_000)==2,'PREOP failed')
  if args.stage=='verify_restore':
   for s in m.slaves[2:]:check(readmap(s,0x1600)==RX and readmap(s,0x1a00)==TX,'Restored mapping differs')
   result['restored_axes']=4
   result['mapped_bytes']=m.config_map();check(m.state_check(pysoem.SAFEOP_STATE,2_000_000)==4,'Restored SAFEOP failed')
   worker=threading.Thread(target=cycle);worker.start();time.sleep(.1)
   with lock:m.state=pysoem.OP_STATE;m.write_state()
   for _ in range(100):
    with lock:state=m.state_check(pysoem.OP_STATE,1000)
    if state==8:break
    time.sleep(.01)
   check(state==8,'Restored OP failed');measuring=True;time.sleep(1)
   check(not errors,str(errors));result['wkc']=dict(expected=m.expected_wkc,count=len(wkc),minimum=min(wkc),maximum=max(wkc),mismatches=sum(x!=m.expected_wkc for x in wkc))
   check(result['wkc']['mismatches']==0,'Restored WKC mismatch')
  elif args.stage=='restore_default':
   baseline=json.loads((ROOT/'before.json').read_text())
   for i,s in enumerate(m.slaves[2:],2):
    old=baseline[i];mapping(s,*[[int.from_bytes(bytes.fromhex(x),'little') for x in old['mapping'][str(ix)][1:]] for ix in [0x1600,0x1a00]])
    for ix in [0x6060,0x6081]:s.sdo_write(ix,0,bytes.fromhex(old['values'][str(ix)]))
    # No pending movement on reconnect: target the current virtual feedback.
    s.sdo_write(0x607a,0,s.sdo_read(0x6064,0));s.sdo_write(0x6040,0,b'\0\0')
   result['mapped_bytes']=m.config_map();check(m.state_check(pysoem.SAFEOP_STATE,2_000_000)==4,'Default SAFEOP failed')
   result['restored_axes']=4
  else:
   for i,s in enumerate(m.slaves[2:],2):
    abort(f'CA read {i}',lambda:s.sdo_read(0x1c12,0,ca=True),0x06010000)
    abort(f'CA write {i}',lambda:s.sdo_write(0x1c12,0,b'\0',ca=True),0x06010000)
    s.sdo_write(0x1c12,0,b'\0');s.sdo_write(0x1600,0,b'\0')
    original=s.sdo_read(0x1600,1)
    abort(f'wrong length {i}',lambda:s.sdo_write(0x1600,1,(0x60400008).to_bytes(4,'little')),0x06040041)
    check(s.sdo_read(0x1600,1)==original,'Rejected write changed candidate')
    s.sdo_write(0x1600,1,(0x60400010).to_bytes(4,'little'));s.sdo_write(0x1600,2,(0x60400010).to_bytes(4,'little'))
    abort(f'duplicate {i}',lambda:s.sdo_write(0x1600,0,b'\2'),0x06040041)
    mapping(s,RX,TX);check(readmap(s,0x1600)==RX and readmap(s,0x1a00)==TX,'Readback mismatch')
    s.sdo_write(0x6060,0,b'\1');s.sdo_write(0x6081,0,(100).to_bytes(4,'little'))
    pos=int.from_bytes(s.sdo_read(0x6064,0),'little',signed=True);s.sdo_write(0x607a,0,(pos+1000).to_bytes(4,'little',signed=True))
   result['mapped_bytes']=m.config_map();result['expected_wkc']=m.expected_wkc
   check(m.state_check(pysoem.SAFEOP_STATE,2_000_000)==4,'SAFEOP failed')
   for i,s in enumerate(m.slaves[2:],2):
    check(len(s.output)==3 and len(s.input)==12,'Dynamic process image size incorrect')
    abort(f'SAFEOP write {i}',lambda:s.sdo_write(0x1c12,0,b'\0'),0x08000022)
   worker=threading.Thread(target=cycle);worker.start();time.sleep(.1)
   with lock:m.state=pysoem.OP_STATE;m.write_state()
   for _ in range(100):
    with lock:state=m.state_check(pysoem.OP_STATE,1000)
    if state==8:break
    time.sleep(.01)
   check(state==8,'OP failed');measuring=True
   for value in [6,7,15]:cw[:]=[value]*4;time.sleep(.2)
   result['enabled']=samples[-1]
   check(all((v[1]&0x6f)==0x27 for v in samples[-1]),'Drive enable failed')
   # F-KR requires reference established before accepting PP targets.
   for s in m.slaves[2:4]:write(s,0x6060,b'\6')
   time.sleep(.1);cw[:2]=[0x1f]*2;time.sleep(.3);cw[:2]=[15]*2;time.sleep(.1)
   result['homing']=samples[-1]
   for s in m.slaves[2:4]:write(s,0x6060,b'\1')
   time.sleep(.1)
   intended=[]
   for s in m.slaves[2:]:
    target=int.from_bytes(read(s,0x6064),'little',signed=True)+1000;intended.append(target)
    write(s,0x607a,target.to_bytes(4,'little',signed=True))
   time.sleep(.1)
   check([int.from_bytes(read(s,0x607a),'little',signed=True) for s in m.slaves[2:]]==intended,'SDO target not retained before PP')
   result['intended_targets']=intended
   cw[:]=[0x3f]*4;time.sleep(.08);cw[:]=[15]*4;time.sleep(2)
   result['after_pp']=samples[-1];result['targets']=[int.from_bytes(read(s,0x607a),'little',signed=True) for s in m.slaves[2:]]
   check(result['targets']==intended,'Target overwritten during PP')
   check(all(abs(v[0]-target)<=20 for v,target in zip(samples[-1],intended)),'PP target not reached')
   check(all(v[2]==1 and v[4]==0 for v in samples[-1]),'Mode or padding feedback incorrect')
   check(all(read(s,0x6081)==(100).to_bytes(4,'little') for s in m.slaves[2:]),'Omitted velocity overwritten')
   check(not errors,str(errors));result['wkc']=dict(count=len(wkc),minimum=min(wkc),maximum=max(wkc),mismatches=sum(x!=m.expected_wkc for x in wkc))
   check(result['wkc']['mismatches']==0,'WKC mismatch')
  result['passed']=True
 except Exception as e:
  result['passed']=False;result['error']=repr(e)
  try:m.read_state();result['states']=[dict(state=s.state,al=s.al_status) for s in m.slaves]
  except Exception:pass
 finally:
  cw[:]=[0]*4
  if worker:time.sleep(.1)
  with lock:
   m.state=pysoem.PREOP_STATE;m.write_state();m.state_check(pysoem.PREOP_STATE,1_000_000)
  stop.set()
  if worker:worker.join(5)
  m.close();result['finished']=time.time();(ROOT/(args.stage+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
