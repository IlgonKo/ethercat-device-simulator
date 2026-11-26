"""Independent station topology and behaviour-instance binding configuration."""
import math
from pathlib import Path
import re
from functional_model.configuration import name, read_json, fields
from device_descriptions.cpx_ap_i_ec.profile import MODULES, contract

SIGNALS = {
    'pneumatic_double_acting': {'extend':'DO','retract':'DO','extended':'DI','retracted':'DI'},
    'analog_delay': {'command':'AO','feedback':'AI'},
}
REQUIRED = {'pneumatic_double_acting': {'extend','retract'}, 'analog_delay': {'command'}}

def station_from_environment(index, identifier, env):
    name(identifier,'IO id')
    prefix=f'DEVICE_SIMULATOR_IO_{identifier}_'
    modules=[]
    for value in env.get(prefix+'MODULES','').split(','):
        parts=[v.strip().upper() for v in value.split(':')]
        if len(parts)<3 or not parts[0].isdigit():raise ValueError('IO modules: expected slot:DI:8 / DO:8 / AIO:4:4')
        modules.append(dict(slot=int(parts[0]),kind=':'.join(parts[1:])))
    bindings=[]
    for value in filter(str.strip,env.get(prefix+'BINDINGS','').split(',')):
        m=re.fullmatch(r'\s*([0-9]+)\s*:\s*(DI|DO|AI|AO)\s*:\s*([0-9]+)\s*=\s*([A-Za-z0-9_-]+)\.([a-z_]+)\s*',value)
        if not m:raise ValueError('IO binding: expected slot:kind:channel=instance.signal')
        bindings.append(dict(slot=int(m[1]),kind=m[2],channel=int(m[3]),instance=m[4],signal=m[5]))
    result=dict(slave_index=index,id=identifier,type='cpx-ap-i-ec',modules=modules,bindings=bindings)
    validate_station(result)
    return result

def validate_station(device):
    modules=device['modules']
    if not isinstance(modules,list) or not 1<=len(modules)<=79:raise ValueError('CPX requires 1..79 supported modules plus interface')
    slots=[]
    for module in modules:
        fields(module,('slot','kind'),'IO module')
        if type(module['slot']) is not int or module['kind'] not in MODULES:raise ValueError('Unsupported IO module')
        slots.append(module['slot'])
    if slots!=list(range(1,len(modules)+1)):raise ValueError('IO module slots must be ordered, contiguous from 1')
    if not isinstance(device['bindings'],list):raise ValueError('IO bindings must be a list')
    contract(device)

def numeric(value, location):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError(f'{location}: finite number required')
    return value

def validate_preset(preset):
    fields(preset,('schema_version','id','model','config'),'model preset')
    if type(preset['schema_version']) is not int or preset['schema_version']!=1:raise ValueError('Unsupported preset schema')
    name(preset['id'],'preset id')
    kind=preset['model'];cfg=preset['config']
    if kind not in SIGNALS or not isinstance(cfg,dict):raise ValueError('Unsupported IO behaviour model')
    allowed={'delay_seconds'} if kind=='analog_delay' else {'stroke','piston_diameter','rod_diameter','moving_mass','sensor_width'}
    if set(cfg)-allowed:raise ValueError('Unknown model preset setting')
    for key,value in cfg.items():numeric(value,key)
    if kind=='analog_delay':
        cfg.setdefault('delay_seconds',.016)
        if not 0<=cfg['delay_seconds']<=10:raise ValueError('delay_seconds: expected 0..10 seconds')
    else:
        minimum={'stroke':.001,'piston_diameter':.001,'rod_diameter':0,'moving_mass':.001,'sensor_width':.00001}
        for k,v in cfg.items():
            if v<minimum[k]:raise ValueError(f'{k}: below FMU minimum {minimum[k]}')
        if cfg.get('rod_diameter',.008)>=cfg.get('piston_diameter',.02):raise ValueError('rod must be smaller than piston')
        if cfg.get('sensor_width',.001)>cfg.get('stroke',.1):raise ValueError('sensor_width exceeds stroke')

def instance_settings_from_environment(env):
    """Parse instance:key:value,key:value,other_instance:key:value groups."""
    raw = env.get('DEVICE_SIMULATOR_IO_MODEL_INSTANCES', '').strip()
    if not raw:
        return {}
    result = {}
    current = None
    for item in raw.split(','):
        parts = [part.strip() for part in item.split(':')]
        if len(parts) == 3:
            identifier, key, value = parts
            name(identifier, 'IO model instance')
            if identifier in result:
                raise ValueError('Duplicate IO model instance settings: ' + identifier)
            current = result[identifier] = {}
        elif len(parts) == 2 and current is not None:
            key, value = parts
        else:
            raise ValueError('IO_MODEL_INSTANCES: expected instance:key:value,key:value; separate instances with commas')
        if not key or key in current:
            raise ValueError('IO_MODEL_INSTANCES: duplicate or empty setting: ' + key)
        current[key] = numeric(float(value), key)
    return result

def models_from_environment(env, devices, preset_root=None, base_directory=None):
    legacy = {key for key in env if key.startswith(('DEVICE_SIMULATOR_BEHAVIOUR_', 'DEVICE_SIMULATOR_MODEL_')) and key != 'DEVICE_SIMULATOR_MODEL_TIMEOUT_MS'}
    if legacy:
        raise ValueError('Retired IO model settings; use IO_MODELS and IO_MODEL_INSTANCES: ' + str(sorted(legacy)))
    instance_settings = instance_settings_from_environment(env)
    root=Path(preset_root) if preset_root is not None else Path(__file__).resolve().parents[3]/'model_presets'
    declarations=list(filter(str.strip,env.get('DEVICE_SIMULATOR_IO_MODELS','').split(',')))
    presets={}
    if declarations:
        for file in sorted(root.rglob('*.json')):
            preset=read_json(file);validate_preset(preset)
            if preset['id'] in presets:raise ValueError('Duplicate preset ID: '+preset['id'])
            presets[preset['id']]=preset
    folder=env.get('DEVICE_SIMULATOR_FMU_DIR','./model_artifacts').strip()
    if not folder:raise ValueError('DEVICE_SIMULATOR_FMU_DIR: nonempty path required')
    artifact_directory=str((Path(base_directory or Path.cwd())/folder).resolve())
    result=[];ids=set()
    for declaration in declarations:
        parts=[v.strip() for v in declaration.split(':')]
        if len(parts)!=2:raise ValueError('IO_MODELS: expected instance:preset')
        identifier,preset_id=parts;name(identifier,'model id')
        if identifier in ids:raise ValueError('Duplicate behaviour instance')
        ids.add(identifier)
        if preset_id not in presets:raise ValueError('Unknown model preset: '+preset_id)
        preset=presets[preset_id];values=instance_settings.get(identifier,{})
        if preset['model']=='analog_delay' and identifier in instance_settings:raise ValueError('analog_delay has no instance settings')
        if set(values)-{'supply_gauge_pressure','opposing_force','initial_position'}:raise ValueError('Unsupported instance setting')
        if values.get('supply_gauge_pressure',0)<0:raise ValueError('supply pressure must be nonnegative')
        if not 0<=values.get('initial_position',0)<=preset['config'].get('stroke',.1):raise ValueError('initial_position outside stroke')
        result.append(dict(id=identifier,preset=preset,instance_config=values,artifact_directory=artifact_directory))
    unknown=set(instance_settings)-ids
    if unknown:raise ValueError('Settings for undeclared IO model instances: '+str(sorted(unknown)))
    station_keys={f"DEVICE_SIMULATOR_IO_{d['id']}_{suffix}" for d in devices if d['type']=='cpx-ap-i-ec' for suffix in ['MODULES','BINDINGS']}
    unknown={k for k in env if k.startswith('DEVICE_SIMULATOR_IO_')}-station_keys-{'DEVICE_SIMULATOR_IO_MODELS','DEVICE_SIMULATOR_IO_MODEL_INSTANCES'}
    if unknown:raise ValueError('Unknown IO settings: '+str(sorted(unknown)))
    validate_bindings(devices,result)
    return result

def validate_bindings(devices, models):
    by_id={m['id']:m for m in models}
    if len(by_id)!=len(models):raise ValueError('Duplicate behaviour instance')
    for m in models:validate_preset(m['preset'])
    used_channels=set();used_signals=set()
    for device in devices:
        if device['type']!='cpx-ap-i-ec':continue
        channels={(c['slot'],c['kind'],c['channel']) for c in contract(device)['channels']}
        for b in device['bindings']:
            fields(b,('slot','kind','channel','instance','signal'),'binding')
            if type(b['slot']) is not int or type(b['channel']) is not int:raise ValueError('Integer slot/channel required')
            key=(b['slot'],b['kind'],b['channel']);ck=(device['id'],)+key;sk=(b['instance'],b['signal'])
            if key not in channels:raise ValueError('Unknown IO channel')
            if b['instance'] not in by_id:raise ValueError('Unknown behaviour instance')
            kind=by_id[b['instance']]['preset']['model']
            if SIGNALS[kind].get(b['signal'])!=b['kind']:raise ValueError('Model signal direction/type mismatch')
            if ck in used_channels or sk in used_signals:raise ValueError('Bindings must be globally 1:1')
            used_channels.add(ck);used_signals.add(sk)
