"""CMMT-compatible identity and extensions, separate from CiA402 semantics."""
from importlib.resources import files
from types import SimpleNamespace
import json
from functools import lru_cache
import xml.etree.ElementTree as ET
from .catalog import parse_cmmt_esi_catalog

@lru_cache(maxsize=1)
def catalog():
    folder = files(__package__)
    identity = json.loads(folder.joinpath('identity.json').read_text())
    return parse_cmmt_esi_catalog('as', folder.joinpath('esi', identity['esi']))

class CmmtAsDescription:
    def __init__(self, mode):
        if mode not in ('linear', 'rotary'):
            raise ValueError('Unsupported axis mode')
        folder = files(__package__)
        self.identity = json.loads(folder.joinpath('identity.json').read_text())
        self.extensions = json.loads(folder.joinpath('extensions.json').read_text())
        self.catalog = catalog()
        if (self.catalog.product_code, self.catalog.revision) != (self.identity['product_code'], self.identity['revision']):
            raise ValueError('ESI identity differs from device description')
        self.vendor_id = int(ET.parse(self.catalog.path).findtext('Vendor/Id').replace('#x', '0x'), 0)
        self.preset = 'linear_mm' if mode == 'linear' else 'rotary_deg'
        preset = self.extensions['presets'][self.preset]
        self.parameters = SimpleNamespace(name=preset['name'], values=tuple(SimpleNamespace(**x) for x in preset['values']))

    def write_sdo(self, adapter, index, sub, payload, access, save):
        previous = adapter.read_sdo(index, sub, len(payload)) if access != 'wo' else None
        adapter.write_sdo(index, sub, payload)
        # CMMT-specific save command; no PDO tick is needed in PRE-OP.
        if save and (index, sub) == (0x2005, 1) and payload == b'\x01':
            try:
                if adapter.od.read(0x2005, 3) != 1:
                    raise ValueError('Only parameter save selection 1 is supported')
                save()
            except Exception:
                if previous is not None: adapter.write_sdo(index, sub, previous)
                raise
            for role, value in [('parameter_save_status', 0),
                                ('parameter_save_return_code', 0),
                                ('parameter_save_return_value', 1)]:
                adapter.od.write_role(role, value)
