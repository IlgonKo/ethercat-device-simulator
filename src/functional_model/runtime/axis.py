from functional_model.cia402_drive.profile.codec import normalize_od_data_type
from functional_model.runtime.provenance import source_hash
import time
import hashlib
import json
from functional_model.cia402_drive.adapter.registry import create_adapter
from functional_model.diagnostics.python_timing import stamp

TYPES = {'uint8': 'USINT', 'int8': 'SINT', 'uint16': 'UINT', 'int16': 'INT',
         'uint32': 'UDINT', 'int32': 'DINT', 'float32': 'REAL'}

class Model:
    def __init__(self, device=None):
        self.device = device or dict(slave_index=0, id="axis-0", type="cia402-drive",
                                     model=dict(type="f_kr_cmmt", mode="linear"), parameter_set="axis-0")
        self.store = None
        self.timing = None
        self.preset = "linear_mm" if self.device["model"]["mode"] == "linear" else "rotary_deg"
        self.adapter = create_adapter(self.device)
        self.profile = self.adapter.profile
        self.rx = self.profile.pdo_configuration.rxpdo_objects()
        self.tx = self.profile.pdo_configuration.txpdo_objects()
        self.rx_size = sum(x.byte_length for x in self.rx)
        self.tx_size = sum(x.byte_length for x in self.tx)
        addresses = {(x.index, x.subindex) for x in self.rx + self.tx if x.index}
        addresses.update((x.index, x.subindex) for x in self.profile.required_non_pdo_od_roles())
        self.entries = {}
        for index, subindex in sorted(addresses):
            d = self.adapter.od.definition(index, subindex)
            dtype = normalize_od_data_type(d.data_type)
            if dtype not in TYPES or d.bit_size not in (8, 16, 32):
                raise ValueError(f'Unsupported required entry {index:04x}:{subindex}: {dtype}')
            self.entries[index, subindex] = dict(index=index, subindex=subindex,
                name=d.name, type=TYPES[dtype], bits=d.bit_size, access=d.access.lower(),
                initial=self.adapter.read_sdo(index, subindex, d.bit_size // 8).hex())
        self.last_cycle = None
        self.cycles = 0
        self.source_hash = source_hash()

    def describe(self):
        catalog = self.profile.esi_catalog
        vendor_id = self.profile.description.vendor_id
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

    def close(self):
        close = getattr(self.adapter, 'close', None)
        if close: close()

    def persistent_roles(self):
        return getattr(self.adapter, 'persistent_roles', self.profile.persistent_roles)

    def parameter_values(self):
        # Profile configuration parameters, not control/status/target/runtime data.
        return {f'{r.index:04x}:{r.subindex:02x}':
                self.adapter.read_sdo(r.index, r.subindex,
                    self.adapter.od.definition(r.index, r.subindex).bit_size // 8).hex()
                for r in self.persistent_roles()}

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
                return {'data': self.adapter.read_sdo(index, sub, entry['bits'] // 8).hex()}
            payload = bytes.fromhex(request['data'])
            if len(payload) != entry['bits'] // 8:
                raise ValueError('SDO length mismatch')
            save = (lambda: self.store.save(self)) if self.store else None
            self.profile.description.write_sdo(self.adapter, index, sub, payload,
                                              entry['access'], save)
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
                self.adapter.apply_outputs(payload)
                after_rx = stamp()
                self.adapter.step(dt)
                after_model = stamp()
                result = self.adapter.read_inputs().hex()
                after_tx = stamp()
                key = f"axis_{self.device['slave_index']}_"
                self.timing.add(key+'rxpdo', begin, after_rx)
                self.timing.add(key+'model', after_rx, after_model)
                self.timing.add(key+'txpdo', after_model, after_tx)
                self.timing.add(key+'cycle_core', begin, after_tx)
            else:
                self.adapter.apply_outputs(payload)
                self.adapter.step(dt)
                result = self.adapter.read_inputs().hex()
            self.cycles += 1
            return {'data': result, 'cycles': self.cycles}
        if op == 'idle':
            self.last_cycle = None
            return {'data': self.adapter.read_inputs().hex()}
        raise ValueError(f'Unknown operation: {op}')


