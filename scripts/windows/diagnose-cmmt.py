#!/usr/bin/env python3
"""RF-003 physical CMMT-AS model test; no Motion Server or Axis Panel required."""
import argparse
import json
from pathlib import Path
import queue
import shlex
import struct
import subprocess
import threading
import time
import traceback
import uuid
import pysoem


def require(ok, message):
    if not ok: raise RuntimeError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-root',required=True,help='Linux path to selected Motion Server source')
    parser.add_argument('--ssh-host',default='Edge-ubuntu')
    parser.add_argument('--remote-repo',default='/home/festo/Documents/ethercat-device-simulator')
    parser.add_argument('--nic',default='enp1s0')
    parser.add_argument('--adapter-guid',default='906A65C9-C606-4B1F-8384-2625829A4D18')
    args=parser.parse_args()
    run_id=uuid.uuid4().hex
    folder=Path(__file__).resolve().parents[2]/'build/diagnostics'/run_id
    folder.mkdir(parents=True)
    report=dict(run_id=run_id,passed=False,arguments=vars(args),samples=[],cleanup_errors=[])
    master=pysoem.Master();remote=None;opened=False;lines=queue.Queue();log=[]
    stage='start'
    def read_remote():
        for line in remote.stdout:
            log.append(line)
            try:lines.put(json.loads(line))
            except json.JSONDecodeError:pass
        lines.put(None)
    def event(timeout):
        value=lines.get(timeout=timeout)
        require(value is not None,'SSH ended unexpectedly')
        return value
    try:
        command=['python3','-u',args.remote_repo+'/scripts/linux/cmmt-session.py',
                 '--run-id',run_id,'--nic',args.nic,'--model-root',args.model_root,'--timeout','600']
        remote=subprocess.Popen(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=10',args.ssh_host,
                                 shlex.join(command)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,text=True,encoding='utf-8')
        threading.Thread(target=read_remote,daemon=True).start()
        ready=event(40);report['ready']=ready
        require(ready['event']=='ready',str(ready))
        spec=ready['contract']
        adapter=next(a for a in pysoem.find_adapters() if args.adapter_guid.upper().strip('{}') in a.name.upper())
        master.open(adapter.name);opened=True
        stage='discovery'
        require(master.config_init()==1,'Expected one CMMT simulator')
        slave=master.slaves[0]
        require((slave.man,slave.id,slave.rev)==(spec['vendor'],spec['product'],spec['revision']),'Unexpected identity')
        require(master.state_check(pysoem.PREOP_STATE,2000000)==pysoem.PREOP_STATE,'PRE-OP failed')
        print('CMMT-AS discovered; validating SDO bridge',flush=True)
        stage='sdo'
        # Required non-PDO parameter: write -> read -> restore before OP.
        original=slave.sdo_read(0x6083,0)
        try:
            slave.sdo_write(0x6083,0,struct.pack('<I',1234))
            require(slave.sdo_read(0x6083,0)==struct.pack('<I',1234),'SDO bridge write/read failed')
        finally:
            slave.sdo_write(0x6083,0,original)
            require(slave.sdo_read(0x6083,0)==original,'SDO restoration failed')
        report['sdo']={'index':'0x6083:0','original':original.hex(),'written':1234,'restored':True}
        stage='mapping'
        master.config_map()
        require((len(slave.output),len(slave.input))==(24,14),'Unexpected PDO mapping lengths')
        require(master.expected_wkc==3,'Expected WKC 3')
        require(master.state_check(pysoem.SAFEOP_STATE,2000000)==pysoem.SAFEOP_STATE,'SAFE-OP failed')
        def exchange(cw=0,mode=8,target=0):
            payload=struct.pack('<HbiIihihB',cw,mode,target,100,0,0,0,0,0)
            slave.output=payload
            master.send_processdata();wkc=master.receive_processdata(20000)
            data=bytes(slave.input)
            require(wkc==3,f'WKC {wkc} at {stage}')
            sw,display,position,velocity,torque,padding=struct.unpack('<HbiihB',data)
            sample=dict(stage=stage,wkc=wkc,status=sw,mode=display,position=position,
                        velocity=velocity,output=payload.hex(),input=data.hex())
            report['samples'].append(sample)
            time.sleep(.01)
            return sample
        stage='op'
        exchange()
        master.state=pysoem.OP_STATE;master.write_state()
        for _ in range(100):
            exchange()
            if master.state_check(pysoem.OP_STATE,1000)==pysoem.OP_STATE:break
        else:raise RuntimeError('OP failed')
        print('OP reached; validating CiA 402 and homing',flush=True)
        def until(cw,mode,target,predicate,count=100):
            for _ in range(count):
                sample=exchange(cw,mode,target)
                if predicate(sample):return sample
            raise RuntimeError(f'Timeout at {stage}: {sample}')
        for stage,cw,sw in [('shutdown',6,0x21),('switch_on',7,0x23),('enable',15,0x27)]:
            until(cw,6,0,lambda s,sw=sw:s['status']&0x6f==sw)
        stage='homing'
        until(15,6,0,lambda s:s['mode']==6)
        home=until(31,6,0,lambda s:bool(s['status']&0x8000),count=200)
        report['homing']=home
        stage='csp_mode'
        until(15,8,0,lambda s:s['mode']==8)
        stage='move'
        initial=exchange(15,8,0)['position']
        for _ in range(1000):sample=exchange(15,8,10000)
        require(sample['position']>initial+100,'Position did not advance through the model')
        require(abs(sample['position']-10000)<100,'Model did not approach target')
        require(sample['status']&0x6f==0x27,'Drive left Operation Enabled')
        stage='sdo_pdo_consistency'
        exchange(15,8,10000)
        sdo_pos=int.from_bytes(slave.sdo_read(0x6064,0),'little',signed=True)
        after=exchange(15,8,10000)
        require(abs(sdo_pos-after['position'])<=2,'SDO/PDO actual-position disagreement')
        report['position']={'initial':initial,'final':sample['position'],'sdo':sdo_pos,'pdo':after['position']}
        stage='disable'
        until(6,8,10000,lambda s:s['status']&0x6f==0x21)
        require(master.state_check(pysoem.OP_STATE,1000)==pysoem.OP_STATE,'EtherCAT left OP')
        report['passed']=True
        print('PASS: SDO restore, CiA 402, homing, movement, 1000 PDO cycles, SDO/PDO consistency',flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        report.update(error=repr(exc),failed_stage=stage)
        (folder/'exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
        print(f'FAIL {stage}: {exc}',flush=True)
        if opened:
            try:
                master.read_state();report['failure_states']=[dict(state=s.state,al_status=s.al_status) for s in master.slaves]
            except Exception:pass
    finally:
        if opened:
            try:
                master.state=pysoem.INIT_STATE;master.write_state()
                require(master.state_check(pysoem.INIT_STATE,2000000)==pysoem.INIT_STATE,'INIT cleanup failed')
            except Exception as exc:report['cleanup_errors'].append(repr(exc))
            finally:
                try:master.close()
                except Exception as exc:report['cleanup_errors'].append(repr(exc))
        if remote:
            try:
                if remote.poll() is None:
                    remote.stdin.write('stop\n');remote.stdin.flush();remote.stdin.close()
                remote.wait(timeout=15)
                finished=None
                while True:
                    item=lines.get(timeout=3)
                    if item is None:break
                    if item.get('event')=='finished':finished=item
                report['remote_cleanup']=finished
                require(remote.returncode==0 and finished and finished['ok'],'Remote cleanup failed')
            except Exception as exc:
                report['cleanup_errors'].append(repr(exc))
                if remote.poll() is None:remote.terminate()
        report['passed']=report['passed'] and not report['cleanup_errors']
        (folder/'remote-session.log').write_text(''.join(log),encoding='utf-8')
        (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Result: {folder / "result.json"}',flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
