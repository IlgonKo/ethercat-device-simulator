from pathlib import Path
import json
from .axis import Model
from device_descriptions.cmmt_as.fixture import generate_fixture

class ModelFleet:
    def __init__(self, config, store):
        self.config = config
        self.models = [Model(device) for device in config['devices']]
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

