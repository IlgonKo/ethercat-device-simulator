import json,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parent
clock=json.loads((BASE/'master/clock.json').read_text())
if (BASE/'master/clock-after.json').exists():clock+=json.loads((BASE/'master/clock-after.json').read_text())
offset=statistics.median(x['offset_s'] for x in clock)
rows=[]
for run in sorted((BASE/'master').glob('*/result.json')):
 name=run.parent.name;data=json.loads(run.read_text());assert data['passed'],name
 logs=[]
 for f in (BASE/name).glob('*.log'):
  for line in f.read_text(errors='replace').splitlines():
   try:rec=json.loads(line)
   except ValueError:continue
   if rec.get('event') in ('simulator-timing','python-timing'):logs.append(rec)
 samples=[json.loads(s) for s in (run.parent/'samples.jsonl').read_text().splitlines()]
 for phase,bounds in data['phases'].items():
  lo=bounds['start']+offset+1;hi=bounds['end']+offset-1
  metrics={};windows={};failures=0
  for rec in logs:
   end=rec['unix_ms']/1000;start=end-rec['window_s']
   if start<lo or end>hi:continue
   event=rec['event'];windows[event]=windows.get(event,0)+1;failures+=rec.get('ipc_failures',0)
   for key,v in rec['metrics'].items():
    k=event+':'+key;n=v['count'];item=metrics.setdefault(k,dict(count=0,total_ms=0,max_ms=0))
    item['count']+=n;item['total_ms']+=v['avg_ms']*n;item['max_ms']=max(item['max_ms'],v['max_ms'])
  assert len(windows)==2 and min(windows.values())>=20,(name,phase,windows)
  for v in metrics.values():v['avg_ms']=v.pop('total_ms')/v['count']
  ss=[s for s in samples if s['phase']==phase];gaps=sorted(s['gap_ms'] for s in ss if s['gap_ms'] is not None)
  rows.append(dict(run=name,mode='docker' if name.startswith('docker') else 'native',axes=data['axes'],phase=phase,
    windows=windows,metrics=metrics,ipc_failures=failures,master=bounds,expected_wkc=data['expected_wkc'],
    tx_gap_mean_ms=statistics.mean(gaps),tx_gap_max_ms=max(gaps),tx_gap_p95_ms=gaps[int(.95*(len(gaps)-1))]))
summary=[]
for mode in ('docker','native'):
 for axes in (2,4):
  for phase in ('stationary','moving'):
   trials=[r for r in rows if (r['mode'],r['axes'],r['phase'])==(mode,axes,phase)];assert len(trials)==2
   def avg(key):
    values=[t['metrics'][key] for t in trials];return sum(v['avg_ms']*v['count'] for v in values)/sum(v['count'] for v in values)
   def maximum(key):return max(t['metrics'][key]['max_ms'] for t in trials)
   summary.append(dict(mode=mode,axes=axes,phase=phase,
    reply_avg_ms=avg('simulator-timing:rx_to_reply'),reply_max_ms=maximum('simulator-timing:rx_to_reply'),
    busy_avg_ms=avg('simulator-timing:frame_busy'),busy_max_ms=maximum('simulator-timing:frame_busy'),
    model_sum_avg_ms=sum(avg(f'python-timing:axis_{i}_model') for i in range(axes)),
    ipc_avg_ms=statistics.mean(avg(f'simulator-timing:ipc_async_axis_{i}') for i in range(axes)),
    ipc_max_ms=max(maximum(f'simulator-timing:ipc_async_axis_{i}') for i in range(axes)),
    master_samples=sum(t['master']['samples'] for t in trials),wkc_mismatches=sum(t['master']['wkc_mismatches'] for t in trials),
    faults=sum(t['master']['faults'] for t in trials),legs=sum(t['master']['legs'] for t in trials),
    ipc_failures=sum(t['ipc_failures'] for t in trials),tx_gap_max_ms=max(t['tx_gap_max_ms'] for t in trials)))
result=dict(clock_offset_s=offset,clock_samples=clock,window_margin_s=1,trials=rows,summary=summary)
(BASE/'summary.json').write_text(json.dumps(result,indent=2))
for row in summary:print(json.dumps(row))
