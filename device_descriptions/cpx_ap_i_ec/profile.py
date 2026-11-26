"""Limited CPX-AP-I-EC profile. Values transcribed from Festo ESI revision 2.

SlotIndexIncrement=16 (AP-Slot override), SlotPdoIncrement=1.
No runtime dependency on Motion Server or vendor ESI parsing.
"""
from copy import deepcopy

MODULES = {
    'DI:8': ('CPX-AP-I-8DI-M8-3P', 0x2007),
    'DO:8': ('CPX-AP-I-8DO-M8-3P', 0x2139),
    'AIO:4:4': ('CPX-AP-I-4AI4AO-U-I-M12', 0x2134),
}

def entry(index, sub, bits, value=0, access='ro', **extra):
    return dict(index=index, subindex=sub, bits=bits, type={1:'BOOL',8:'USINT',16:'UINT',32:'UDINT'}[bits],
                name=f'{index:04X}:{sub:02X}', access=access,
                initial=int(value).to_bytes((bits+7)//8,'little').hex(), **extra)

def contract(device):
    entries=[]; pdos=[]; channels=[]
    def add(index, sub, bits, value=0, access='ro', **extra):
        e=entry(index,sub,bits,value,access,**extra);entries.append(e);return e
    add(0x1000,0,32,72749961);add(0x1001,0,8)
    add(0x1018,0,8,4)
    for sub,value in enumerate([29,8086609,2,device['slave_index']+1],1):add(0x1018,sub,32,value)
    add(0x6102,0,8,4)
    for sub,bits in enumerate([32,16,16,32],1):add(0x6102,sub,bits)
    # MDP metadata: index distance, maximum modules, supported list information.
    add(0xf000,0,8,2);add(0xf000,1,16,16);add(0xf000,2,16,80)
    idents=[0x2084]+[MODULES[m['kind']][1] for m in device['modules']]
    for index in [0xf030,0xf050]:
        access='rw' if index==0xf030 else 'ro'
        add(index,0,8,len(idents),access)
        for sub,v in enumerate(idents,1):add(index,sub,32,v,access)
    for m in device['modules']:
        slot=m['slot']; kind=m['kind']
        for direction in ['rx','tx']:
            digital=(kind=='DO:8' and direction=='rx') or (kind=='DI:8' and direction=='tx')
            if not digital and kind!='AIO:4:4':continue
            index=(0x7000 if direction=='rx' else 0x6000)+slot*16
            count=8 if digital else 4
            group=[];add(index,0,8,8 if kind=='AIO:4:4' and direction=='rx' else count)
            for channel in range(count):
                e=add(index,channel+1,1 if digital else 16,rx=direction=='rx',tx=direction=='tx')
                if not digital:e['type']='INT'
                group.append(deepcopy(e))
                channels.append(dict(slot=slot,kind=('DO' if direction=='rx' else 'DI') if digital else ('AO' if direction=='rx' else 'AI'),channel=channel,index=index,subindex=channel+1,bits=e['bits']))
            if kind=='AIO:4:4' and direction=='rx':
                for sub in range(5,9):group.append(add(index,sub,1,rx=True,tx=False))
                group.append(dict(index=0,subindex=0,bits=4))
            pdos.append(dict(index=(0x1600 if direction=='rx' else 0x1a00)+slot,direction=direction,entries=group))
    for d,assignment in [('rx',0x1c12),('tx',0x1c13)]:
        selected=[p for p in pdos if p['direction']==d]
        add(assignment,0,8,len(selected))
        for sub,p in enumerate(selected,1):
            add(assignment,sub,16,p['index']);add(p['index'],0,8,len(p['entries']))
            for n,e in enumerate(p['entries'],1):add(p['index'],n,32,(e['index']<<16)|(e['subindex']<<8)|e['bits'])
    result=dict(protocol=3,profile='cpx-ap-i-ec',vendor=29,product=8086609,revision=2,
                entries=entries,pdos=pdos,channels=channels)
    for d in ['rx','tx']:
        result[d]=[e for p in pdos if p['direction']==d for e in p['entries']]
        result[d+'_size']=(sum(e['bits'] for e in result[d])+7)//8
        if result[d+'_size']>1024:raise ValueError('CPX process image exceeds 1024 bytes')
    return result
