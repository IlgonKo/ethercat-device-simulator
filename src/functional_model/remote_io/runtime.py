"""8 ms IO model scheduler, independent of EtherCAT receive/IPC request rate.

One worker per behaviour instance; no queued steps, no catch-up and no overlap
within an instance. The IO lock is never held while a behaviour model computes.
The factory receives a validated preset and instance settings, and returns an
adapter with initial_outputs(), step(inputs, time, dt), close(). Actual FMU
adapters are supplied by the next implementation stage; tests inject fixtures.
"""
import json
import os
import threading
import time
import uuid
from .configuration import REQUIRED, SIGNALS

DT=.008

def create_adapter(spec):
    raise ValueError(f"IO FMU adapter not installed yet: {spec['preset']['model']}; RF-013 stage 4 required")

def validate_value(kind, value):
    if kind in ('DI','DO'):
        if type(value) is not bool:raise ValueError('Digital IO requires bool')
    elif type(value) is not int or not -32768<=value<=32767:
        raise ValueError('Analog IO requires signed Int16 without clamping')
    return value

class IORuntime:
    def __init__(self, stations, specs, factory=create_adapter, timeout=None, autostart=True):
        self.lock=threading.RLock();self.stop=threading.Event();self.workers=[]
        self.timeout=float(timeout if timeout is not None else int(os.environ.get('DEVICE_SIMULATOR_MODEL_TIMEOUT_MS','100'))/1000)
        if not .01<=self.timeout<=5:raise ValueError('Model timeout must be 10..5000 ms')
        self.host_failed=False;self.session=None;self.diagnostics=[];self.instances={}
        self.stations={s.device['slave_index']:dict(station=s,active=False,sequence=0,values={}) for s in stations}
        self.outputs={}
        for idx,s in self.stations.items():
            self.outputs[idx]={(e['index'],e['subindex']):e['initial'] for e in s['station'].contract['entries'] if e.get('tx')}
        try:
            for spec in specs:
                ident=spec['id'];kind=spec['preset']['model'];links={}
                for idx,s in self.stations.items():
                    channels={(c['slot'],c['kind'],c['channel']):c for c in s['station'].contract['channels']}
                    for b in s['station'].device['bindings']:
                        if b['instance']==ident:links[b['signal']]=(idx,channels[b['slot'],b['kind'],b['channel']])
                dependencies={links[k][0] for k in REQUIRED[kind] if k in links}
                adapter=factory(spec)
                item=dict(id=ident,kind=kind,adapter=adapter,links=links,dependencies=dependencies,
                          complete=REQUIRED[kind]<=set(links),barrier={i:0 for i in dependencies},paused=True,
                          steps=0,fault=None,busy_since=None,late_steps=0,last_duration=0.)
                self.instances[ident]=item
                self._publish(item,adapter.initial_outputs())
            if autostart:
                for item in self.instances.values():
                    worker=threading.Thread(target=self._worker,args=(item,),daemon=True,name='io-'+item['id'])
                    self.workers.append(worker);worker.start()
        except Exception:
            self.close();raise

    def _diagnostic(self, item, code, detail):
        now=time.time();source={'type':'model_host','index':0} if item is None else {'type':'behaviour_model','id':item['id']}
        diagnostic=dict(event='diagnostic',action='detected',diagnostic_id=str(uuid.uuid4()),
            definition=dict(code=code,level='fault',title=code,description=detail,latching=True),
            source=source,history=dict(occurred_at=now,acknowledged_at=None,resolved_at=None),
            detail=detail,context=dict(feedback_valid=False,restart_required=True))
        self.diagnostics.append(diagnostic);print(json.dumps(diagnostic),flush=True)

    def _check_timeout(self, now):
        if self.host_failed:return
        if any(m['busy_since'] is not None and now-m['busy_since']>=self.timeout for m in self.instances.values()):
            self.host_failed=True
            self._diagnostic(None,'MODEL_RESPONSE_TIMEOUT','IO model computation deadline exceeded; manual restart required')

    def _pause(self, item):
        if not item['paused']:
            item['paused']=True
            item['barrier']={i:self.stations[i]['sequence'] for i in item['dependencies']}

    def _ready(self, item):
        if not item['complete'] or item['fault'] or self.host_failed:return False
        if not all(self.stations[i]['active'] for i in item['dependencies']):
            self._pause(item);return False
        if item['paused']:
            if not all(self.stations[i]['sequence']>item['barrier'][i] for i in item['dependencies']):return False
            item['paused']=False
        return True

    def exchange(self, request):
        with self.lock:
            self._check_timeout(time.monotonic())
            session=request['session']
            if self.session is not None and session!=self.session:raise ValueError('IO session cannot change without restart')
            self.session=session
            updates=request['stations']
            if {s['slave_index'] for s in updates}!=set(self.stations) or len(updates)!=len(self.stations):raise ValueError('Complete unique station snapshot required')
            validated=[]
            for update in updates:
                idx=update['slave_index'];station=self.stations[idx]
                sequence=update['sequence'];active=update['active']
                if type(sequence) is not int or sequence<station['sequence'] or type(active) is not bool:raise ValueError('Invalid IO snapshot sequence/state')
                expected={(e['index'],e['subindex']):e for e in station['station'].contract['entries'] if e.get('rx')}
                values={}
                for v in update['values']:
                    key=(v['index'],v['subindex'])
                    if key not in expected or key in values:raise ValueError('Invalid IO output address')
                    raw=bytes.fromhex(v['data']);e=expected[key]
                    if len(raw)!=(e['bits']+7)//8:raise ValueError('Invalid IO output size')
                    value=int.from_bytes(raw,'little',signed=e['bits']==16)
                    if e['bits']==1:
                        if value not in (0,1):raise ValueError('Invalid digital IO value')
                        value=bool(value)
                    values[key]=value
                if values.keys()!=expected.keys():raise ValueError('Incomplete IO output snapshot')
                validated.append((station,sequence,active,values))
            for station,sequence,active,values in validated:
                station.update(sequence=sequence,active=active,values=values)
            for item in self.instances.values():
                if not all(self.stations[i]['active'] for i in item['dependencies']):self._pause(item)
            return dict(session=session,request_id=request['request_id'],host_failed=self.host_failed,
                        stations=[dict(slave_index=i,values=[dict(index=k[0],subindex=k[1],data=v) for k,v in values.items()]) for i,values in self.outputs.items()])

    def _publish(self,item,outputs):
        expected={k:v for k,v in SIGNALS[item['kind']].items() if v in ('DI','AI')}
        if set(outputs)!=set(expected):raise ValueError('Incomplete or unknown model output')
        prepared=[]
        for signal,kind in expected.items():
            v=validate_value(kind,outputs[signal])
            if signal in item['links']:
                idx,c=item['links'][signal]
                data=int(v).to_bytes((c['bits']+7)//8,'little',signed=c['bits']==16).hex()
                prepared.append((idx,(c['index'],c['subindex']),data))
        for idx,key,data in prepared:self.outputs[idx][key]=data

    def step_once(self, identifier):
        """One scheduler opportunity. Also permits deterministic contract tests."""
        item=self.instances[identifier]
        with self.lock:
            now=time.monotonic();self._check_timeout(now)
            if self.stop.is_set() or item['busy_since'] is not None or not self._ready(item):return False
            inputs={signal:self.stations[idx]['values'][c['index'],c['subindex']] for signal,(idx,c) in item['links'].items() if SIGNALS[item['kind']][signal] in ('DO','AO')}
            item['busy_since']=now;model_time=item['steps']*DT
        try:
            outputs=item['adapter'].step(inputs,model_time,DT)
            with self.lock:
                self._check_timeout(time.monotonic())
                if not self.host_failed and not self.stop.is_set():
                    self._publish(item,outputs);item['steps']+=1
        except Exception as exc:
            with self.lock:
                if not self.host_failed:
                    item['fault']=str(exc);self._diagnostic(item,'MODEL_CALCULATION_FAILED',str(exc))
        finally:
            with self.lock:
                elapsed=time.monotonic()-item['busy_since'];item['last_duration']=elapsed
                if elapsed>DT:item['late_steps']+=1
                item['busy_since']=None
        return True

    def _worker(self, item):
        try:
            while not self.stop.is_set():
                start=time.monotonic()
                self.step_once(item['id'])
                # Drop elapsed deadlines. Never replay missed ticks or overlap.
                self.stop.wait(max(0,DT-(time.monotonic()-start)))
        finally:
            item['adapter'].close()

    def close(self):
        self.stop.set()
        for worker in self.workers:worker.join(timeout=.2)
        if not self.workers:
            for item in self.instances.values():item['adapter'].close()
