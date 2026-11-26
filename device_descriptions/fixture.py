from pathlib import Path
import json
import xml.etree.ElementTree as ET


def write_fixture(contract, destination):
    fixed = contract.get('profile') == 'cpx-ap-i-ec'
    spec = dict(contract) if fixed else dict(contract, rx_size=0, tx_size=0, rx=[], tx=[])
    device_type = 'CPX_AP_I_EC_SIM' if fixed else 'CMMT_AS_SIM'
    root = ET.Element('EtherCATInfo', Version='1.6')
    def child(parent, name, value=None, **attrs):
        el = ET.SubElement(parent, name, attrs)
        if value is not None: el.text = str(value)
        return el
    vendor = child(root, 'Vendor')
    child(vendor, 'Id', f"#x{spec['vendor']:08X}")
    child(vendor, 'Name', 'Festo identity - simulation test fixture')
    descriptions = child(root, 'Descriptions')
    group = child(child(descriptions, 'Groups'), 'Group')
    child(group, 'Type', 'CMMT_SIM'); child(group, 'Name', 'CMMT simulation')
    dev = child(child(descriptions, 'Devices'), 'Device', Physics='YY')
    child(dev, 'Type', device_type, ProductCode=f"#x{spec['product']:08X}", RevisionNo=f"#x{spec['revision']:08X}")
    child(dev, 'Name', 'CPX-AP-I-EC limited software profile' if fixed else 'CMMT-AS software model (limited test fixture)')
    child(dev, 'GroupType', 'CMMT_SIM')
    profile = child(dev, 'Profile'); child(profile, 'ProfileNo', 5001 if fixed else 402)
    dictionary = child(profile, 'Dictionary')
    types = child(dictionary, 'DataTypes'); objects = child(dictionary, 'Objects')
    for name, bits in [('BOOL',1),('USINT',8),('SINT',8),('UINT',16),('INT',16),('UDINT',32),('DINT',32),('REAL',32)]:
        dt = child(types, 'DataType'); child(dt, 'Name', name); child(dt, 'BitSize', bits)
    groups = {}
    for entry in spec['entries']: groups.setdefault(entry['index'], []).append(entry)
    def value(index, sub, name, typ, bits, number):
        return dict(index=index, subindex=sub, name=name, type=typ, bits=bits, access='ro',
                    initial=number.to_bytes((bits+7)//8, 'little').hex())
    groups.setdefault(0x1000, [value(0x1000,0,'Device type','UDINT',32,402)])
    groups.setdefault(0x1018, [value(0x1018,0,'Count','USINT',8,4)] + [value(0x1018,i,n,'UDINT',32,v) for i,n,v in
        [(1,'Vendor',spec['vendor']),(2,'Product',spec['product']),(3,'Revision',spec['revision']),(4,'Serial',1)]])
    groups[0x1c00] = [value(0x1c00,i,f'SM{i}','USINT',8,v) for i,v in enumerate([4,1,2,3,4])]
    # Explicit CA alignment for all communication arrays. KickCAT's automatic
    # assignment/mapping builders also start subindex 1 at bit 8.
    for index, key, assignment in ([] if fixed else [(0x1600, 'rx', 0x1c12), (0x1a00, 'tx', 0x1c13)]):
        groups[index] = [value(index, 0, 'Count', 'USINT', 8, 0)]
        for sub in range(1, 17):
            groups[index].append(value(index, sub, f'Mapping {sub}', 'UDINT', 32, 0))
        groups[assignment] = [value(assignment, 0, 'Count', 'USINT', 8, 0),
                              value(assignment, 1, 'PDO', 'UINT', 16, 0)]
        for entry in groups[index] + groups[assignment]: entry['access'] = 'rw'
    for index, entries in sorted(groups.items()):
        entries = sorted(entries,key=lambda e:e['subindex'])
        obj = child(objects, 'Object'); child(obj, 'Index', f'#x{index:04X}')
        child(obj,'Name',f'Simulator object {index:04X}')
        if len(entries)==1 and entries[0]['subindex']==0:
            e=entries[0]
            child(obj,'Type',e['type']); child(obj,'BitSize',e['bits'])
            child(child(obj,'Info'),'DefaultData',e['initial'])
            child(child(obj,'Flags'),'Access',e['access'] or 'ro')
        else:
            if entries[0]['subindex'] != 0:
                entries.insert(0,value(index,0,'Count','USINT',8,max(e['subindex'] for e in entries)))
            typename=f'SIM_{index:04X}'
            dt=child(types,'DataType'); child(dt,'Name',typename)
            total=16+sum(e['bits'] for e in entries[1:])
            child(dt,'BitSize',total); child(obj,'Type',typename); child(obj,'BitSize',total)
            info=child(obj,'Info'); offset=0
            for e in entries:
                name=f"Sub {e['subindex']} {e['name']}"
                sub=child(dt,'SubItem')
                for key,v in [('SubIdx',e['subindex']),('Name',name),('Type',e['type']),('BitSize',e['bits']),('BitOffs',offset)]:child(sub,key,v)
                child(child(sub,'Flags'),'Access',e['access'] or 'ro')
                default=child(info,'SubItem'); child(default,'Name',name)
                child(child(default,'Info'),'DefaultData',e['initial'])
                offset=16 if e['subindex']==0 else offset+e['bits']
    child(dev,'Fmmu','Outputs'); child(dev,'Fmmu','Inputs')
    for name,size,address,control in [('MBoxOut',128,0x1000,0x26),('MBoxIn',128,0x1400,0x22),
                                     ('Outputs',spec['rx_size'],0x1800,0x64),('Inputs',spec['tx_size'],0x1c00,0x20)]:
        child(dev,'Sm',name,DefaultSize=str(size),StartAddress=f'#x{address:04X}',ControlByte=f'#x{control:02X}',Enable='1')
    pdos = spec['pdos'] if fixed else [dict(direction=k,index=i,entries=spec[k]) for k,i in [('rx',0x1600),('tx',0x1a00)]]
    for desc in pdos:
        key=desc['direction']; tag='RxPdo' if key=='rx' else 'TxPdo'
        pdo=child(dev,tag,Fixed='1' if fixed else '0',Mandatory='1' if fixed else '0',Sm='2' if key=='rx' else '3')
        child(pdo,'Index',f"#x{desc['index']:04X}"); child(pdo,'Name',tag)
        for e in desc['entries']:
            entry=child(pdo,'Entry')
            for name,v in [('Index',f"#x{e['index']:04X}"),('SubIndex',e['subindex']),('BitLen',e['bits']),('Name',e.get('name','Padding')),('DataType',e.get('type','USINT'))]:child(entry,name,v)
    child(child(dev,'Mailbox',DataLinkLayer='true'),'CoE',SdoInfo='true',CompleteAccess='false',PdoAssign='false' if fixed else 'true',PdoConfig='false' if fixed else 'true')
    eeprom=child(dev,'Eeprom'); child(eeprom,'ByteSize',2048); child(eeprom,'ConfigData','8002006EFF00FF000000')
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(destination/'cmmt.xml',encoding='utf-8',xml_declaration=True)
    (destination/'cmmt.json').write_text(json.dumps({'esi':'cmmt.xml','device_type':device_type}),encoding='utf-8')
    (destination/'contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
    return contract

