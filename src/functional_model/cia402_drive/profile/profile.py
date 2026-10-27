"""CiA402 interface definitions composed with an EtherCAT device description.

No motion algorithm, state machine, or Master initialization methods live here.
"""
import json
from importlib.resources import files
from types import SimpleNamespace
from .pdo import PdoConfiguration
from .metadata import ObjectDictionaryEntry

class CiA402DriveProfile:
    name = 'cia402-drive'

    def __init__(self, description):
        self.description = description
        self.esi_catalog = description.catalog
        self.non_pdo_configuration = description.parameters
        self.pdo_configuration = PdoConfiguration()
        standard = json.loads(files(__package__).joinpath('roles.json').read_text())
        roles = {r['role']: SimpleNamespace(**r) for r in standard + description.extensions['roles']}
        self.roles = tuple(roles[key] for key in description.extensions['role_order'])
        self.persistent_roles = tuple(roles[key] for key in description.extensions['persistent_roles'])

    def required_non_pdo_od_roles(self): return self.roles
    def object_dictionary_entries(self): return tuple(self.esi_catalog.objects.items())

    @staticmethod
    def expected_data_type_bits(data_type):
        return ObjectDictionaryEntry(0, 0, '', data_type).bit_length

    def validate_catalog_support(self):
        for entry in self.roles + self.pdo_configuration.rx + self.pdo_configuration.tx:
            if not entry.index: continue
            actual = self.esi_catalog.object_info(entry.index, entry.subindex)
            if actual.bit_size != self.expected_data_type_bits(entry.data_type):
                raise ValueError(f'ESI bit size mismatch: {entry.index:04x}:{entry.subindex}')
