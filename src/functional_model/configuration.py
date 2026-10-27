"""Simulator-owned environment configuration and persistent-data validation."""
import copy
import json
from pathlib import Path
import re
import shlex


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


def validate_config(data, base_directory):
    data = copy.deepcopy(data)
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
    data['storage']['directory'] = str((Path(base_directory) / root).resolve())
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
        if device['type'] != 'cia402-drive':
            raise ValueError(f'{loc}.type: only cia402-drive axes are supported; IO is deferred')
        model = device['model']
        if not isinstance(model, dict): raise ValueError(f'{loc}.model: object required')
        kind = model.get('type')
        fields(model, ('type', 'mode', 'artifact') if kind == 'copley_drive_sim' else ('type', 'mode'), f'{loc}.model')
        if kind not in ('f_kr_cmmt', 'copley_drive_sim') or model['mode'] not in ('linear', 'rotary'):
            raise ValueError(f'{loc}.model: expected f_kr_cmmt/copley_drive_sim with linear or rotary mode')
        if kind == 'copley_drive_sim':
            if not isinstance(model['artifact'], str) or not model['artifact'].strip():
                raise ValueError(f'{loc}.model.artifact: path required')
            model['artifact'] = str((Path(base_directory) / model['artifact']).resolve())
    if indices != set(range(len(devices))):
        raise ValueError('devices.slave_index: must be contiguous from 0 to N-1')
    data['devices'] = sorted(devices, key=lambda d: d['slave_index'])
    return data


def read_env(path):
    """Read literal dotenv assignments (quoted values, comments, continuations).

    No shell execution or variable expansion. Docker Compose handles its own
    env_file parsing; keep device configuration values literal in both paths.
    """
    result = {}
    pending = ''
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if line.rstrip().endswith('\\'):
            pending += line.rstrip()[:-1]
            continue
        line = (pending + line).strip()
        pending = ''
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        if not match:
            raise ValueError('Expected KEY=value in environment file')
        key, raw = match.groups()
        if key in result:
            raise ValueError(f'Duplicate environment key: {key}')
        parts = shlex.split(raw, comments=True, posix=True)
        value = ' '.join(parts)
        if '$' in value or '`' in value:
            raise ValueError(f'{key}: use literal values, not shell expansion')
        result[key] = value
    if pending:
        raise ValueError('Unfinished environment continuation')
    return result


def load_environment(env, base_directory=None):
    if 'DEVICE_SIMULATOR_CONFIG_FILE' in env:
        raise ValueError('DEVICE_SIMULATOR_CONFIG_FILE removed; configure DEVICE_SIMULATOR_BUS in .env')
    def required(key):
        value = env.get(key, '')
        if not value.strip():
            raise ValueError(f'{key}: required')
        return value.strip()
    mappings = {}
    keys = ('IDS', 'MODELS', 'MODES', 'PARAMETER_SETS')
    for suffix in keys:
        key = 'DEVICE_SIMULATOR_AXIS_' + suffix
        values = {}
        for entry in required(key).split(','):
            match = re.fullmatch(r'\s*(0|[1-9][0-9]*)\s*:\s*([^:,]+?)\s*', entry)
            if not match or int(match[1]) in values:
                raise ValueError(f'{key}: expected unique index:value entries')
            values[int(match[1])] = match[2].strip()
        mappings[suffix] = values
    devices = []
    indices = set()
    for entry in required('DEVICE_SIMULATOR_BUS').split(','):
        match = re.fullmatch(r'\s*(0|[1-9][0-9]*)\s*:\s*axis\s*:\s*(cia402-drive)\s*', entry)
        if not match:
            raise ValueError('DEVICE_SIMULATOR_BUS: expected explicit index:axis:cia402-drive entries')
        index = int(match[1])
        if index in indices:
            raise ValueError('DEVICE_SIMULATOR_BUS: duplicate slave index')
        indices.add(index)
        if any(index not in values for values in mappings.values()):
            raise ValueError(f'Missing axis mapping for slave {index}')
        devices.append(dict(slave_index=index, id=mappings['IDS'][index], type=match[2],
                            model=dict(type=mappings['MODELS'][index], mode=mappings['MODES'][index]),
                            parameter_set=mappings['PARAMETER_SETS'][index]))
    if any(set(values) != indices for values in mappings.values()):
        raise ValueError('Axis mapping indices must exactly match DEVICE_SIMULATOR_BUS')
    allowed = {'DEVICE_SIMULATOR_AXIS_' + key for key in keys}
    unused = {key for key in env if key.startswith('DEVICE_SIMULATOR_AXIS_')} - allowed
    if unused:
        raise ValueError(f'Unknown axis settings: {sorted(unused)}')
    for device in devices:
        if device['model']['type'] == 'copley_drive_sim':
            folder = env.get('DEVICE_SIMULATOR_FMU_DIR', './model_artifacts').strip()
            if not folder: raise ValueError('DEVICE_SIMULATOR_FMU_DIR: nonempty path required')
            device['model']['artifact'] = str(Path(folder) / 'CopleyDriveSim-linux.fmu')
    state = required('DEVICE_SIMULATOR_STATE_DIR')
    data = dict(schema_version=1, ethercat=dict(interface=required('KICKCAT_INTERFACE')),
                storage=dict(directory=str(Path(state))), devices=devices)
    return validate_config(data, base_directory or Path.cwd())


def load_config(path):
    """Load device configuration exclusively from a literal .env file."""
    path = Path(path).resolve(strict=True)
    return load_environment(read_env(path), path.parent)
