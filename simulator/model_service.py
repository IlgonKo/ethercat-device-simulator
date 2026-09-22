"""RF-003 local model service. Imports an explicitly selected Motion Server checkout."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulator.configuration import load_config
from simulator.parameter_store import ParameterStore
from simulator.python_timing import PythonTiming, stamp

MAX_MESSAGE = 1024 * 1024
TYPES = {'uint8': 'USINT', 'int8': 'SINT', 'uint16': 'UINT', 'int16': 'INT',
         'uint32': 'UDINT', 'int32': 'DINT', 'float32': 'REAL'}


class Model:
    def __init__(self, model_root, device=None):
        self.device = device or dict(slave_index=0, id="axis-0", type="cmmt-as",
                                     model=dict(type="virtual_axis", mode="linear"), parameter_set="axis-0")
        self.store = None
        self.timing = None
        self.preset = "linear_mm" if self.device["model"]["mode"] == "linear" else "rotary_deg"
        model_root = Path(model_root).resolve(strict=True)
        if not (model_root / 'device/virtual_device/od_bridge.py').is_file():
            raise ValueError('Selected model root does not contain VirtualOdBridge')
        sys.path.insert(0, str(model_root))
        from device.cmmt.profile import CMMTASDeviceProfile
        from device.cmmt.non_pdo_configuration import get_non_pdo_configuration
        from device.virtual_device.od_bridge import VirtualOdBridge
        from device.virtual_servo_drive.servo_model import VirtualCiA402Servo
        from device.od_value_codec import normalize_od_data_type
        self.profile = CMMTASDeviceProfile(axis_index=self.device["slave_index"], slave_index=self.device["slave_index"])
        # Explicit existing model preset; physical drive parameters are not changed.
        self.profile.non_pdo_configuration = get_non_pdo_configuration(self.preset)
        self.servo = VirtualCiA402Servo(cycle_time=0.01, device_profile=self.profile)
        self.bridge = VirtualOdBridge(self.servo.od, self.profile.pdo_configuration)
        self.rx = self.profile.pdo_configuration.rxpdo_objects()
        self.tx = self.profile.pdo_configuration.txpdo_objects()
        self.rx_size = sum(x.byte_length for x in self.rx)
        self.tx_size = sum(x.byte_length for x in self.tx)
        addresses = {(x.index, x.subindex) for x in self.rx + self.tx if x.index}
        addresses.update((x.index, x.subindex) for x in self.profile.required_non_pdo_od_roles())
        self.entries = {}
        for index, subindex in sorted(addresses):
            d = self.servo.od.definition(index, subindex)
            dtype = normalize_od_data_type(d.data_type)
            if dtype not in TYPES or d.bit_size not in (8, 16, 32):
                raise ValueError(f'Unsupported required entry {index:04x}:{subindex}: {dtype}')
            self.entries[index, subindex] = dict(index=index, subindex=subindex,
                name=d.name, type=TYPES[dtype], bits=d.bit_size, access=d.access.lower(),
                initial=self.bridge.read_sdo(index, subindex, d.bit_size // 8).hex())
        self.last_cycle = None
        self.cycles = 0
        self.model_root = str(model_root)
        # Record all source/data inputs in the selected dependency tree, without
        # publishing or copying those files into the simulator's source tree.
        digest = hashlib.sha256()
        inputs = []
        for directory in ('device', 'configuration', 'motion_server', 'ethercat'):
            inputs.extend(p for p in (model_root / directory).rglob('*')
                          if p.is_file() and p.suffix in ('.py', '.xml', '.json'))
        inputs.append(model_root / 'Reference/cmmt_error_catalog.json')
        for path in sorted(inputs):
            digest.update(path.relative_to(model_root).as_posix().encode())
            digest.update(b'\0')
            digest.update(path.read_bytes())
        self.source_hash = digest.hexdigest()

    def describe(self):
        catalog = self.profile.esi_catalog
        vendor = ET.parse(catalog.path).findtext('Vendor/Id')
        vendor_id = int(vendor.replace('#x', '0x'), 0)
        def mapping(objects):
            return [dict(index=x.index, subindex=x.subindex, bits=x.bit_length,
                         name=x.name, type=self.entries[x.index, x.subindex]['type'] if x.index else 'USINT')
                    for x in objects]
        result = dict(protocol=1, profile='cmmt_as', pdo='motion_server_default',
                      preset=self.preset, model_source_hash=self.source_hash,
                      vendor=vendor_id, product=catalog.product_code,
                      revision=catalog.revision, rx_size=self.rx_size, tx_size=self.tx_size,
                      entries=list(self.entries.values()), rx=mapping(self.rx), tx=mapping(self.tx))
        result['contract_hash'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result

    def parameter_values(self):
        # Profile configuration parameters, not control/status/target/runtime data.
        from device.cmmt.required_non_pdo_od import NON_PDO_CONFIGURATION_OD_ROLES
        return {f'{r.index:04x}:{r.subindex:02x}':
                self.bridge.read_sdo(r.index, r.subindex,
                    self.servo.od.definition(r.index, r.subindex).bit_size // 8).hex()
                for r in NON_PDO_CONFIGURATION_OD_ROLES}

    def dispatch(self, request):
        op = request['op']
        if op == 'describe':
            return self.describe()
        if op in ('read', 'write'):
            index, sub = request['index'], request['subindex']
            entry = self.entries[index, sub]
            if op == 'read':
                if entry['access'] == 'wo':
                    raise ValueError('Write-only object')
                return {'data': self.bridge.read_sdo(index, sub, entry['bits'] // 8).hex()}
            payload = bytes.fromhex(request['data'])
            if len(payload) != entry['bits'] // 8:
                raise ValueError('SDO length mismatch')
            previous = self.bridge.read_sdo(index, sub, len(payload)) if entry['access'] != 'wo' else None
            self.bridge.write_sdo(index, sub, payload)
            # Persist synchronously in the SDO path, also in PRE-OP without PDO ticks.
            if self.store and (index, sub) == (0x2005, 1) and payload == b'\x01':
                try:
                    if self.servo.od.read(0x2005, 3) != 1:
                        raise ValueError('Only parameter save selection 1 is supported')
                    self.store.save(self)
                except Exception:
                    if previous is not None: self.bridge.write_sdo(index, sub, previous)
                    raise
                for role, value in [('parameter_save_status', 0),
                                    ('parameter_save_return_code', 0),
                                    ('parameter_save_return_value', 1)]:
                    self.servo.od.write_role(role, value)
            return {}
        if op == 'cycle':
            payload = bytes.fromhex(request['data'])
            if len(payload) != self.rx_size:
                raise ValueError('RxPDO length mismatch')
            now = time.monotonic()
            dt = 0.01 if self.last_cycle is None else now - self.last_cycle
            if dt > 0.1:
                raise RuntimeError('PDO gap exceeds 100 ms; restart the test session')
            self.last_cycle = now
            if self.timing:
                begin = stamp()
                self.bridge.rxpdo_payload_to_od(payload)
                after_rx = stamp()
                self.servo.cycle_time = dt
                self.servo.model_update()
                after_model = stamp()
                result = self.bridge.od_to_txpdo_payload().hex()
                after_tx = stamp()
                key = f"axis_{self.device['slave_index']}_"
                self.timing.add(key+'rxpdo', begin, after_rx)
                self.timing.add(key+'model', after_rx, after_model)
                self.timing.add(key+'txpdo', after_model, after_tx)
                self.timing.add(key+'cycle_core', begin, after_tx)
            else:
                self.bridge.rxpdo_payload_to_od(payload)
                self.servo.cycle_time = dt
                self.servo.model_update()
                result = self.bridge.od_to_txpdo_payload().hex()
            self.cycles += 1
            return {'data': result, 'cycles': self.cycles}
        if op == 'idle':
            self.last_cycle = None
            return {'data': self.bridge.od_to_txpdo_payload().hex()}
        raise ValueError(f'Unknown operation: {op}')


class ModelFleet:
    def __init__(self, model_root, config, store):
        self.config = config
        self.models = [Model(model_root, device) for device in config['devices']]
        # Validate every existing snapshot before creating any missing snapshot.
        missing = []
        for model in self.models:
            model.store = store
            if not store.load(model): missing.append(model)
        for model in missing: store.save(model)

    def describe(self):
        return dict(protocol=2, devices=[dict(device=m.device, contract=m.describe()) for m in self.models])

    def dispatch(self, request):
        if request['op'] == 'describe': return self.describe()
        index = request.get('slave_index')
        if type(index) is not int or not 0 <= index < len(self.models):
            raise ValueError('IPC slave_index is required and must be in range')
        return self.models[index].dispatch(request)

    def generate_fixture(self, destination):
        destination = Path(destination).resolve()
        paths = []
        for model in self.models:
            folder = destination / str(model.device['slave_index'])
            generate_fixture(model, folder)
            paths.append(str(folder / 'cmmt.json'))
        (destination / 'cmmt.json').write_text(json.dumps(dict(slaves=paths)), encoding='utf-8')
        (destination / 'contract.json').write_text(json.dumps(self.describe(), indent=2), encoding='utf-8')


def generate_fixture(model, destination):
    """Generate a limited simulator ESI from the selected model contract, not a drive ESI clone."""
    spec = model.describe()
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
    child(dev, 'Type', 'CMMT_AS_SIM', ProductCode=f"#x{spec['product']:08X}", RevisionNo=f"#x{spec['revision']:08X}")
    child(dev, 'Name', 'CMMT-AS software model (limited test fixture)')
    child(dev, 'GroupType', 'CMMT_SIM')
    profile = child(dev, 'Profile'); child(profile, 'ProfileNo', 402)
    dictionary = child(profile, 'Dictionary')
    types = child(dictionary, 'DataTypes'); objects = child(dictionary, 'Objects')
    for name, bits in [('USINT',8),('SINT',8),('UINT',16),('INT',16),('UDINT',32),('DINT',32),('REAL',32)]:
        dt = child(types, 'DataType'); child(dt, 'Name', name); child(dt, 'BitSize', bits)
    groups = {}
    for entry in spec['entries']: groups.setdefault(entry['index'], []).append(entry)
    def value(index, sub, name, typ, bits, number):
        return dict(index=index, subindex=sub, name=name, type=typ, bits=bits, access='ro',
                    initial=number.to_bytes(bits//8, 'little').hex())
    groups[0x1000] = [value(0x1000,0,'Device type','UDINT',32,402)]
    groups[0x1018] = [value(0x1018,0,'Count','USINT',8,4)] + [value(0x1018,i,n,'UDINT',32,v) for i,n,v in
        [(1,'Vendor',spec['vendor']),(2,'Product',spec['product']),(3,'Revision',spec['revision']),(4,'Serial',1)]]
    groups[0x1c00] = [value(0x1c00,i,f'SM{i}','USINT',8,v) for i,v in enumerate([4,1,2,3,4])]
    # Explicit CA alignment for all communication arrays. KickCAT's automatic
    # assignment/mapping builders also start subindex 1 at bit 8.
    for index, key, assignment in [(0x1600, 'rx', 0x1c12), (0x1a00, 'tx', 0x1c13)]:
        groups[index] = [value(index, 0, 'Count', 'USINT', 8, len(spec[key]))]
        for sub, e in enumerate(spec[key], 1):
            word = (e['index'] << 16) | (e['subindex'] << 8) | e['bits']
            groups[index].append(value(index, sub, f'Mapping {sub}', 'UDINT', 32, word))
        groups[assignment] = [value(assignment, 0, 'Count', 'USINT', 8, 1),
                              value(assignment, 1, 'PDO', 'UINT', 16, index)]
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
    for tag,key,index,sm in [('RxPdo','rx',0x1600,2),('TxPdo','tx',0x1a00,3)]:
        pdo=child(dev,tag,Fixed='1',Mandatory='1',Sm=str(sm))
        child(pdo,'Index',f'#x{index:04X}'); child(pdo,'Name',tag)
        for e in spec[key]:
            entry=child(pdo,'Entry')
            for name,v in [('Index',f"#x{e['index']:04X}"),('SubIndex',e['subindex']),('BitLen',e['bits']),('Name',e['name']),('DataType',e['type'])]:child(entry,name,v)
    child(child(dev,'Mailbox',DataLinkLayer='true'),'CoE',SdoInfo='true',CompleteAccess='true',PdoAssign='false',PdoConfig='false')
    eeprom=child(dev,'Eeprom'); child(eeprom,'ByteSize',2048); child(eeprom,'ConfigData','8002006EFF00FF000000')
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(destination/'cmmt.xml',encoding='utf-8',xml_declaration=True)
    (destination/'cmmt.json').write_text(json.dumps({'esi':'cmmt.xml','device_type':'CMMT_AS_SIM'}),encoding='utf-8')
    (destination/'contract.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
    return spec


def serve(model, path, timing=None):
    # Caller supplies a private session directory; never unlink an existing socket.
    path=Path(path)
    if path.exists(): raise FileExistsError(path)
    if path.parent.stat().st_mode & 0o077: raise ValueError('Socket directory must have mode 0700')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(path)); os.chmod(path,0o600); server.listen(1); server.settimeout(30)
        print(json.dumps({'event':'model-ready','socket':str(path)}),flush=True)
        try:
            conn,_=server.accept()
            with conn,conn.makefile('rwb') as stream:
                # The owning session bounds lifetime; an idle EtherCAT link is
                # not by itself an IPC failure. Client RPCs have a 1 s timeout.
                conn.settimeout(None)
                while True:
                    raw=stream.readline(MAX_MESSAGE+1)
                    if not raw: break
                    if len(raw)>MAX_MESSAGE or not raw.endswith(b'\n'): raise ValueError('Invalid IPC message length')
                    # Fail closed: no successful SDO/PDO response after a model exception.
                    if timing:
                        begin = stamp()
                        request = json.loads(raw)
                        after_parse = stamp()
                        response = model.dispatch(request)
                        after_dispatch = stamp()
                        encoded = json.dumps(response,separators=(',',':')).encode()+b'\n'
                        after_encode = stamp()
                        stream.write(encoded); stream.flush()
                        after_send = stamp()
                        op = request['op']
                        timing.add(op+'_json_decode', begin, after_parse)
                        timing.add(op+'_dispatch', after_parse, after_dispatch)
                        timing.add(op+'_json_encode', after_dispatch, after_encode)
                        timing.add(op+'_send', after_encode, after_send)
                        timing.add(op+'_request', begin, after_send)
                        timing.due()
                    else:
                        response=model.dispatch(json.loads(raw))
                        stream.write(json.dumps(response,separators=(',',':')).encode()+b'\n'); stream.flush()
        finally:
            if timing: timing.flush("stop")
            path.unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model-root',required=True)
    p.add_argument('--config')
    p.add_argument('--fixture-dir')
    p.add_argument('--socket')
    p.add_argument('--timing', action='store_true')
    args=p.parse_args()
    if not args.fixture_dir and not args.socket:p.error('Specify --fixture-dir or --socket')
    with ExitStack() as stack:
        if args.config:
            config = load_config(args.config)
            store = stack.enter_context(ParameterStore(config['storage']['directory']))
            model = ModelFleet(args.model_root, config, store)
            if args.fixture_dir: model.generate_fixture(args.fixture_dir)
        else:
            # Explicit original one-axis feasibility harness, without persistence.
            model = Model(args.model_root)
            if args.fixture_dir: generate_fixture(model,args.fixture_dir)
        print(json.dumps(model.describe()), flush=True)
        timing = None
        if args.timing:
            models = model.models if isinstance(model, ModelFleet) else [model]
            timing = PythonTiming(len(models))
            for item in models: item.timing = timing
        if args.socket: serve(model,args.socket,timing)



if __name__=='__main__':main()
