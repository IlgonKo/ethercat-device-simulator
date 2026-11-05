import argparse,json,time,threading,struct
from pathlib import Path
import pysoem
RX=[0x60400010,0x60600008,0x607a0020,0x60810020,0x60ff0020,0x60710010,0x60b10020,0x60b20010,8]
TX=[0x60410010,0x60610008,0x60640020,0x606c0020,0x60770010,8]
def main():
 p=argparse.ArgumentParser();p.add_argument('--axes',type=int,choices=(2,4),required=True);p.add_argument('--output',required=True);p.add_argument('--seconds',type=float,default=30);a=p.parse_args()
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 m=pysoem.Master();m.open(r'\Device\NPF_{906A65C9-C606-4B1F-8384-2625829A4D18}')
 n=a.axes;lock=threading.Lock();stop=threading.Event();worker=None;errors=[];samples=[];phase='prepare';feedback=[]
 cw=[0]*n;mode=[1]*n;target=[0]*n;result={'axes':n,'cycle_ms':4,'seconds':a.seconds,'phases':{}}
 def check(ok,msg):
  if not ok:raise RuntimeError(msg)
 def cycle():
  nonlocal feedback
  due=time.perf_counter();previous=None
  try:
   while not stop.is_set():
    with lock:
     for j,s in enumerate(m.slaves):
      s.output=bytes(len(s.output)) if j<2 else struct.pack('<HbiIihihB',cw[j-2],mode[j-2],target[j-2],10,0,0,0,0,0)
     start=time.perf_counter();stamp=time.time();m.send_processdata();wkc=m.receive_processdata(3000);end=time.perf_counter()
     feedback=[struct.unpack('<HbiihB',s.input) for s in m.slaves[2:]]
     samples.append({'time':stamp,'phase':phase,'wkc':wkc,'gap_ms':None if previous is None else (start-previous)*1000,'exchange_ms':(end-start)*1000,'feedback':feedback})
     previous=start
    due+=.004;time.sleep(max(0,due-time.perf_counter()))
  except Exception as e:errors.append(repr(e));stop.set()
 def wait_until(fn,timeout=10):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   check(not errors,str(errors))
   if feedback and fn(feedback):return
   time.sleep(.01)
  raise TimeoutError('Motion/state timeout '+repr(feedback))
 try:
  check(m.config_init()==n+2,'Unexpected slave count')
  check(all(s.man==29 and s.id==8067733 and s.rev==36120 for s in m.slaves[2:]),'Virtual identities mismatch')
  result['identities']=[dict(name=s.name,man=s.man,id=s.id,rev=s.rev) for s in m.slaves]
  m.state=2;m.write_state();check(m.state_check(2,2000000)==2,'PREOP failed')
  for s in m.slaves[2:]:
   for assign,pdo,items in [(0x1c12,0x1600,RX),(0x1c13,0x1a00,TX)]:
    s.sdo_write(assign,0,b'\0');s.sdo_write(pdo,0,b'\0')
    for sub,item in enumerate(items,1):s.sdo_write(pdo,sub,item.to_bytes(4,'little'))
    s.sdo_write(pdo,0,bytes([len(items)]));s.sdo_write(assign,1,pdo.to_bytes(2,'little'));s.sdo_write(assign,0,b'\1')
  m.config_map();result['expected_wkc']=m.expected_wkc
  check(m.state_check(4,2000000)==4,'SAFEOP failed')
  worker=threading.Thread(target=cycle);worker.start();time.sleep(.1)
  with lock:m.state=8;m.write_state()
  for _ in range(100):
   with lock:state=m.state_check(8,1000)
   if state==8:break
   time.sleep(.01)
  check(state==8,'OP failed')
  for value in (6,7,15):cw[:]=[value]*n;time.sleep(.1)
  wait_until(lambda f:all((v[0]&0x6f)==0x27 for v in f))
  for i in range(0,n,2):mode[i]=6
  time.sleep(.1)
  for i in range(0,n,2):cw[i]=31
  wait_until(lambda f:all(f[i][0]&0x8000 for i in range(0,n,2)))
  cw[:]=[15]*n;time.sleep(.1);mode[:]=[1]*n;time.sleep(.2)
  for name in ('stationary','moving'):
   phase=name;result['phases'][name]={'start':time.time()};deadline=time.monotonic()+a.seconds;legs=0
   if name=='stationary':
    while time.monotonic()<deadline:check(not errors,str(errors));time.sleep(.1)
   else:
    goal=10000
    while time.monotonic()<deadline:
     target[:]=[goal]*n;cw[:]=[15]*n;time.sleep(.04);cw[:]=[0x3f]*n;time.sleep(.04);cw[:]=[15]*n
     wait_until(lambda f:all(abs(v[2]-goal)<=2 and abs(v[3])<=1 for v in f))
     legs+=1;goal=0 if goal else 10000
   result['phases'][name].update(end=time.time(),legs=legs)
   phase='between';time.sleep(.2)
  check(not errors,str(errors))
  for name in result['phases']:
   rows=[x for x in samples if x['phase']==name]
   result['phases'][name].update(samples=len(rows),wkc_mismatches=sum(x['wkc']!=m.expected_wkc for x in rows),faults=sum(any(v[0]&8 for v in x['feedback']) for x in rows))
   check(result['phases'][name]['wkc_mismatches']==0,'WKC mismatch');check(result['phases'][name]['faults']==0,'Axis fault')
  result['passed']=True
 except Exception as e:result.update(passed=False,error=repr(e))
 finally:
  phase='cleanup';cw[:]=[0]*n
  if worker:time.sleep(.1)
  with lock:
   m.state=2;m.write_state();m.state_check(2,1000000)
  stop.set()
  if worker:worker.join(5)
  m.close()
  (out/'result.json').write_text(json.dumps(result,indent=2));(out/'samples.jsonl').write_text('\n'.join(json.dumps(x) for x in samples)+'\n')
  print(json.dumps(result,indent=2))
 if not result.get('passed'):raise SystemExit(1)
if __name__=='__main__':main()
