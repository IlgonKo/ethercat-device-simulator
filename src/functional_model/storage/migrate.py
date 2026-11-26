"""Explicit offline F-KR schema 1/2 -> 3 migration; never run at service startup."""
import argparse
import json
import os
import tempfile
from pathlib import Path

from functional_model.configuration import read_json
from functional_model.runtime.axis import Model
from .parameter_store import ParameterStore


def migrate_profile_velocity(store, model, value):
    return migrate_quick_stop(store, model, profile_velocity=value)


def migrate_quick_stop(store, model, profile_velocity=None):
    if store.lock is None:
        raise RuntimeError('Parameter storage lock is required')
    if model.device['model']['type'] != 'f_kr_cmmt':
        raise ValueError('Only F-KR CMMT migration is supported')
    if profile_velocity is not None and (type(profile_velocity) is not int or not 0 <= profile_velocity <= 0xffffffff):
        raise ValueError('Profile velocity must be an explicit uint32 raw OD value')
    path = store.path(model)
    original = path.read_bytes()
    data = read_json(path)
    if type(data.get('schema_version')) is int and data['schema_version'] == store.schema_version(model):
        store.load(model)
        return False
    if set(data) != {'schema_version', 'identity', 'values', 'checksum'}:
        raise ValueError('Invalid snapshot fields')
    digest = data.pop('checksum')
    if store.checksum(data) != digest:
        raise ValueError('Snapshot checksum mismatch')
    version = data['schema_version']
    if type(version) is not int or version not in (1, 2):
        raise ValueError('Expected schema 1 or 2')
    if version == 1 and profile_velocity is None:
        raise ValueError('Schema 1 requires explicit profile velocity')
    if data['identity'] != store.identity(model):
        raise ValueError('Snapshot identity mismatch')
    expected = set(model.parameter_values()) - {'605a:00', '6085:00'}
    if version == 1:
        expected.remove('6081:00')
    if not isinstance(data['values'], dict) or set(data['values']) != expected:
        raise ValueError('Legacy parameter catalog mismatch')
    if version == 1:
        data['values']['6081:00'] = profile_velocity.to_bytes(4, 'little').hex()
    data['values']['605a:00'] = '0200'
    data['values']['6085:00'] = data['values']['6084:00']
    data['schema_version'] = store.schema_version(model)
    data['checksum'] = store.checksum(data)
    # Use the normal strict loader to validate all existing values before touching
    # the original snapshot. The supplied model must be a fresh offline instance.
    with tempfile.TemporaryDirectory() as temporary:
        staged = ParameterStore(temporary)
        staged.path(model).write_text(json.dumps(data), encoding='utf-8')
        staged.load(model)
    backup = path.with_name(path.name + f'.schema{version}.bak')
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
    parser.add_argument('--axis-id', required=True)
    parser.add_argument('--mode', choices=('linear', 'rotary'), required=True)
    parser.add_argument('--profile-velocity', type=int,
                        help='Explicit raw 0x6081 value; old snapshots do not contain it')
    args = parser.parse_args()
    from functional_model.configuration import name
    try: name(args.axis_id, 'axis id')
    except ValueError as error: parser.error(str(error))
    model = Model(dict(slave_index=0, id=args.axis_id, type='cia402-drive',
                       model=dict(type='f_kr_cmmt', mode=args.mode)))
    try:
        with ParameterStore(args.store) as store:
            changed = migrate_quick_stop(store, model, args.profile_velocity)
        print(json.dumps(dict(axis_id=args.axis_id, migrated=changed)))
    finally:
        model.close()


if __name__ == '__main__':
    main()
