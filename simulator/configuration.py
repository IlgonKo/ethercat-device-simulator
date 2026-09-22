"""Simulator-owned JSON configuration. No Motion Server configuration imports."""
import json
from pathlib import Path
import re


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    def invalid(value):
        raise ValueError(f'Non-standard JSON constant: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=unique_object, parse_constant=invalid)


def fields(value, keys, location):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{location}: required fields exactly {sorted(keys)}')


def name(value, location):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
        raise ValueError(f'{location}: use 1-64 letters, digits, underscores or hyphens')


def load_config(path):
    path = Path(path).resolve(strict=True)
    data = read_json(path)
    fields(data, ('schema_version', 'ethercat', 'storage', 'devices'), '$')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('schema_version: only integer 1 is supported')
    fields(data['ethercat'], ('interface',), 'ethercat')
    nic = data['ethercat']['interface']
    if not isinstance(nic, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', nic):
        raise ValueError('ethercat.interface: invalid Linux interface name')
    fields(data['storage'], ('directory',), 'storage')
    directory = data['storage']['directory']
    if not isinstance(directory, str) or not directory.strip():
        raise ValueError('storage.directory: nonempty path required')
    root = Path(directory)
    data['storage']['directory'] = str((path.parent / root).resolve())
    devices = data['devices']
    if not isinstance(devices, list) or not devices:
        raise ValueError('devices: nonempty array required')
    ids, sets, indices = set(), set(), set()
    for n, device in enumerate(devices):
        loc = f'devices[{n}]'
        fields(device, ('slave_index', 'id', 'type', 'model', 'parameter_set'), loc)
        index = device['slave_index']
        if type(index) is not int or index < 0 or index in indices:
            raise ValueError(f'{loc}.slave_index: unique nonnegative integer required')
        indices.add(index)
        for key, used in (('id', ids), ('parameter_set', sets)):
            name(device[key], f'{loc}.{key}')
            if device[key] in used:
                raise ValueError(f'{loc}.{key}: duplicate {device[key]}')
            used.add(device[key])
        if device['type'] != 'cmmt-as':
            raise ValueError(f'{loc}.type: only cmmt-as axes are supported; IO is deferred')
        fields(device['model'], ('type', 'mode'), f'{loc}.model')
        if device['model']['type'] != 'virtual_axis' or device['model']['mode'] not in ('linear', 'rotary'):
            raise ValueError(f'{loc}.model: expected virtual_axis with linear or rotary mode')
    if indices != set(range(len(devices))):
        raise ValueError('devices.slave_index: must be contiguous from 0 to N-1')
    data['devices'] = sorted(devices, key=lambda d: d['slave_index'])
    return data
