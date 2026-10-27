"""Initial fixed PDO layout; dynamic remapping remains RF-014."""
import json
from importlib.resources import files
from .metadata import ObjectDictionaryEntry

class PdoConfiguration:
    def __init__(self):
        data = json.loads(files(__package__).joinpath('pdo.json').read_text())
        self.name = data['name']
        self.rx = tuple(ObjectDictionaryEntry(**item) for item in data['rx'])
        self.tx = tuple(ObjectDictionaryEntry(**item) for item in data['tx'])

    def rxpdo_objects(self): return self.rx
    def txpdo_objects(self): return self.tx
