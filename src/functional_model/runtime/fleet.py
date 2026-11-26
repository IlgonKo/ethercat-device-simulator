from pathlib import Path
import json
from .axis import Model
from functional_model.remote_io.station import Station
from functional_model.remote_io.runtime import IORuntime
from device_descriptions.cmmt_as.fixture import generate_fixture

class ModelFleet:
    def __init__(self, config, store, io_factory=None):
        self.config = config
        self.models = []
        self.io_runtime = None
        try:
            for device in config['devices']: self.models.append(Station(device) if device['type']=='cpx-ap-i-ec' else Model(device))
            # Validate all snapshots before creating any missing snapshot.
            missing = []
            for model in self.models:
                if isinstance(model,Station):continue
                model.store = store
                if not store.load(model): missing.append(model)
            for model in missing: store.save(model)
            stations=[m for m in self.models if isinstance(m,Station)]
            if stations:
                options={} if io_factory is None else {'factory':io_factory}
                self.io_runtime=IORuntime(stations,config.get('io_models',[]),**options)
        except Exception:
            self.close()
            raise

    def close(self):
        if self.io_runtime:self.io_runtime.close()
        for model in reversed(self.models): model.close()

    def describe(self):
        return dict(protocol=2, devices=[dict(device=m.device, contract=m.describe()) for m in self.models])

    def dispatch(self, request):
        if request['op'] == 'describe': return self.describe()
        if request['op']=='io_exchange' and self.io_runtime:return self.io_runtime.exchange(request)
        index = request.get('slave_index')
        if type(index) is not int or not 0 <= index < len(self.models):
            raise ValueError('IPC slave_index is required and must be in range')
        return self.models[index].dispatch(request)

    def generate_fixture(self, destination):
        destination = Path(destination).resolve()
        paths = []
        for model in self.models:
            folder = destination / str(model.device['slave_index'])
            if isinstance(model,Station):model.generate_fixture(folder)
            else:generate_fixture(model, folder)
            paths.append(str(folder / 'cmmt.json'))
        (destination / 'cmmt.json').write_text(json.dumps(dict(slaves=paths)), encoding='utf-8')
        (destination / 'contract.json').write_text(json.dumps(self.describe(), indent=2), encoding='utf-8')

