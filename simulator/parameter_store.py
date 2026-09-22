"""Versioned, atomically replaced parameter snapshots; runtime state is excluded."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from simulator.configuration import read_json, fields


class ParameterStore:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = None

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = (self.root / '.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.lock.seek(0)
                if not self.lock.read(1):
                    self.lock.write(b'0'); self.lock.flush()
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close(); self.lock = None
            raise RuntimeError(f'Parameter storage already owned: {self.root}') from None
        return self

    def __exit__(self, *args):
        if self.lock:
            self.lock.close(); self.lock = None

    def path(self, model):
        return self.root / (model.device['parameter_set'] + '.json')

    def identity(self, model):
        return {k: model.device[k] for k in ('type', 'model')}

    @staticmethod
    def checksum(data):
        return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def load(self, model):
        path = self.path(model)
        if not path.exists():
            return False
        data = read_json(path)
        fields(data, ('schema_version', 'identity', 'values', 'checksum'), str(path))
        digest = data.pop('checksum')
        if self.checksum(data) != digest:
            raise ValueError(f'{path}: checksum mismatch')
        if type(data['schema_version']) is not int or data['schema_version'] != 1 or data['identity'] != self.identity(model):
            raise ValueError(f'{path}: incompatible parameter schema/type/model/mode')
        expected = model.parameter_values()
        values = data['values']
        if not isinstance(values, dict) or set(values) != set(expected):
            raise ValueError(f'{path}: parameter catalog mismatch')
        # Decode and validate everything before mutating the fresh model.
        from device.od_value_codec import decode_od_value, encode_od_value
        decoded = []
        for key, original in expected.items():
            raw = values[key]
            if not isinstance(raw, str) or len(raw) != len(original):
                raise ValueError(f'{path}: invalid parameter length {key}')
            index, sub = (int(x, 16) for x in key.split(':'))
            definition = model.servo.od.definition(index, sub)
            value = decode_od_value(definition.data_type, bytes.fromhex(raw))
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f'{path}: nonfinite parameter {key}')
            encode_od_value(definition.data_type, value, len(raw)//2)
            # Read-only units must still match this model's defaults.
            if definition.access.lower() == 'ro' and raw != original:
                raise ValueError(f'{path}: incompatible unit/scale {key}')
            decoded.append((index, sub, value))
        for index, sub, value in decoded:
            model.servo.od.write(index, value, sub)
        return True

    def save(self, model):
        if self.lock is None:
            raise RuntimeError('Parameter storage lock is required')
        data = dict(schema_version=1, identity=self.identity(model), values=model.parameter_values())
        data['checksum'] = self.checksum(data)
        target = self.path(model)
        fd, temporary = tempfile.mkstemp(prefix='.' + target.name, dir=self.root)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, indent=2, allow_nan=False)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, target)
            if os.name != 'nt':
                directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
                try: os.fsync(directory)
                finally: os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)
