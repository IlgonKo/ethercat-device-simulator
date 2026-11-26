"""Explicit physical CPX test. Only selected software CPX slaves are put in OP.

Other devices are left in PRE-OP. Does not Enable or move a physical axis.
Requires an idle master NIC and an independently started two-station fixture.
"""
import argparse
import json
import struct
import time
import pysoem

def run(interface,duration):
    master=pysoem.Master();master.open(interface)
    try:
        count=master.config_init()
        inventory=[dict(index=i,name=s.name,manufacturer=s.man,id=s.id,revision=s.rev) for i,s in enumerate(master.slaves)]
        print(json.dumps({'inventory':inventory}),flush=True)
        selected=[i for i,s in enumerate(master.slaves) if s.name=='CPX-AP-I-EC limited software profile']
        assert len(selected)==2, f'Expected two software CPX stations; found {selected}'
        expected_idents=[[0x2084,0x2007,0x2139,0x2134,0x2139],[0x2084,0x2139,0x2007,0x2134]]
        for n,i in enumerate(selected):
            slave=master.slaves[i]
            assert (slave.man,slave.id,slave.rev)==(29,8086609,2)
            idents=[int.from_bytes(slave.sdo_read(0xf050,j),'little') for j in range(1,len(expected_idents[n])+1)]
            assert idents==expected_idents[n],idents
            for j,v in enumerate(idents,1):slave.sdo_write(0xf030,j,struct.pack('<I',v))
            slave.sdo_write(0xf030,0,bytes([len(idents)]))
            for index in [0x1c12,0x1c13]:
                old=slave.sdo_read(index,0)
                for data in [bytes([0]),old]:
                    try:slave.sdo_write(index,0,data)
                    except pysoem.SdoError as exc:assert exc.abort_code==0x06010002
                    else:raise AssertionError('Read-only assignment write succeeded')
                assert slave.sdo_read(index,0)==old
            try:slave.sdo_read(0x27f1,0)
            except pysoem.SdoError as exc:assert exc.abort_code==0x06020000
            else:raise AssertionError('Unsupported AP save request succeeded')
        master.config_map()
        # config_map may request SAFE-OP; explicitly park every unrelated device.
        for i,s in enumerate(master.slaves):
            s.output=bytes(len(s.output));s.state=pysoem.SAFEOP_STATE if i in selected else pysoem.PREOP_STATE;s.write_state()
        for i in selected:assert master.slaves[i].state_check(pysoem.SAFEOP_STATE,500000)==pysoem.SAFEOP_STATE
        for i,s in enumerate(master.slaves):
            if i not in selected:assert s.state_check(pysoem.PREOP_STATE,500000)==pysoem.PREOP_STATE
        for _ in range(20):master.send_processdata();master.receive_processdata(10000);time.sleep(.008)
        for i in selected:master.slaves[i].state=pysoem.OP_STATE;master.slaves[i].write_state()
        for _ in range(30):master.send_processdata();master.receive_processdata(10000);time.sleep(.008)
        for i in selected:assert master.slaves[i].state_check(pysoem.OP_STATE,500000)==pysoem.OP_STATE
        for n,i in enumerate(selected):assert (len(master.slaves[i].output),len(master.slaves[i].input))==((11,9) if n==0 else (10,9))
        expected=6 # two selected stations, one output and one input FMMU each, LRW 2+1
        hist={};start=time.monotonic();cycles=0
        while time.monotonic()-start<duration:
            for n,i in enumerate(selected):
                # DO8, four signed AO16, supply/padding byte, optional following DO8.
                supply=15 if cycles%2 else 0
                payload=bytes([0x81])+struct.pack('<hhhh',-32768,-1,0,32767)+bytes([supply])+(bytes([0x42]) if n==0 else b'')
                master.slaves[i].output=payload
            master.send_processdata();wkc=master.receive_processdata(10000);hist[wkc]=hist.get(wkc,0)+1;cycles+=1
            for i in selected:assert master.slaves[i].input==bytes(9),'Unbound IO is not zero'
            time.sleep(.008)
        assert hist=={expected:cycles},hist
        for n,i in enumerate(selected):
            s=master.slaves[i]
            for sub,v in enumerate([-32768,-1,0,32767],1):
                master.send_processdata();master.receive_processdata(10000)
                assert int.from_bytes(s.sdo_read(0x7030,sub),'little',signed=True)==v
            assert s.sdo_read(0x1001,0)==b'\x00'
            assert s.sdo_read(0x6102,1)==bytes(4)
        return dict(result='passed',selected=selected,slaves=count,duration_seconds=duration,requested_sleep_ms=8,
                    cycles=cycles,wkc_histogram=hist,layouts=[[len(master.slaves[i].output),len(master.slaves[i].input)] for i in selected],
                    scope='CPX basic physical transport; no behaviour FMU or physical axis motion')
    finally:
        master.state=pysoem.PREOP_STATE;master.write_state();master.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--interface',required=True);p.add_argument('--duration',type=float,default=5);p.add_argument('--output');a=p.parse_args()
    result=run(a.interface,a.duration);print(json.dumps(result,indent=2),flush=True)
    if a.output:
        from pathlib import Path
        Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
if __name__=='__main__':main()
