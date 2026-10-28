"""Explicit offline F-KR schema 1 -> 2 migration; never run at service startup."""
import argparse
import json
import os
import tempfile
from pathlib import Path

from functional_model.configuration import read_json
from functional_model.runtime.axis import Model
from .parameter_store import ParameterStore


def migrate_profile_velocity(store, model, value):
    if store.lock is None:
        raise RuntimeError('Parameter storage lock is required')
    if model.device['model']['type'] != 'f_kr_cmmt':
        raise ValueError('Only F-KR CMMT schema 1 migration is supported')
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('Profile velocity must be an explicit uint32 raw OD value')
    path = store.path(model)
    original = path.read_bytes()
    data = read_json(path)
    if type(data.get('schema_version')) is int and data['schema_version'] == 2:
        store.load(model)
        return False
    if set(data) != {'schema_version', 'identity', 'values', 'checksum'}:
        raise ValueError('Invalid snapshot fields')
    digest = data.pop('checksum')
    if store.checksum(data) != digest:
        raise ValueError('Snapshot checksum mismatch')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('Expected schema 1')
    if data['identity'] != store.identity(model):
        raise ValueError('Snapshot identity mismatch')
    expected = set(model.parameter_values()) - {'6081:00'}
    if not isinstance(data['values'], dict) or set(data['values']) != expected:
        raise ValueError('Legacy parameter catalog mismatch')
    data['values']['6081:00'] = value.to_bytes(4, 'little').hex()
    data['schema_version'] = 2
    data['checksum'] = store.checksum(data)
    # Use the normal strict loader to validate all existing values before touching
    # the original snapshot. The supplied model must be a fresh offline instance.
    with tempfile.TemporaryDirectory() as temporary:
        staged = ParameterStore(temporary)
        staged.path(model).write_text(json.dumps(data), encoding='utf-8')
        staged.load(model)
    backup = path.with_name(path.name + '.schema1.bak')
    if backup.exists():
        if backup.read_bytes() != original:
            raise ValueError('Existing migration backup differs; preserve and investigate')
    else:
        with backup.open('xb') as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
    store.save(model)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--parameter-set', required=True)
    parser.add_argument('--mode', choices=('linear', 'rotary'), required=True)
    parser.add_argument('--profile-velocity', required=True, type=int,
                        help='Explicit raw 0x6081 value; old snapshots do not contain it')
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.parameter_set):
        parser.error('Invalid parameter-set name')
    model = Model(dict(slave_index=0, id='migration', type='cia402-drive',
                       parameter_set=args.parameter_set,
                       model=dict(type='f_kr_cmmt', mode=args.mode)))
    try:
        with ParameterStore(args.store) as store:
            changed = migrate_profile_velocity(store, model, args.profile_velocity)
        print(json.dumps(dict(parameter_set=args.parameter_set, migrated=changed)))
    finally:
        model.close()


if __name__ == '__main__':
    main()
