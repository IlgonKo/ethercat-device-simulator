#!/usr/bin/env python3
"""Summarize local Python elapsed/CPU timing without adding nested phases."""
import argparse
import json
from pathlib import Path


def summarize(path, skip_seconds=10):
    metrics = {}
    axes = set()
    windows = 0
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.startswith('{'): continue
        try: record = json.loads(line)
        except json.JSONDecodeError: continue
        if record.get('event') != 'python-timing': continue
        if record['elapsed_s'] - record['window_s'] < skip_seconds: continue
        windows += 1; axes.add(record['axes'])
        for key, b in record['metrics'].items():
            if not b['count']: continue
            a = metrics.setdefault(key, dict(count=0, total_ms=0, cpu_total_ms=0,
                min_ms=b['min_ms'], max_ms=0, cpu_max_ms=0))
            a['count'] += b['count']
            a['total_ms'] += b['count'] * b['avg_ms']
            a['cpu_total_ms'] += b['count'] * b['cpu_avg_ms']
            a['min_ms'] = min(a['min_ms'], b['min_ms'])
            a['max_ms'] = max(a['max_ms'], b['max_ms'])
            a['cpu_max_ms'] = max(a['cpu_max_ms'], b['cpu_max_ms'])
    if not windows or len(axes) != 1: raise ValueError('Expected timing windows from one axis count')
    for a in metrics.values():
        a['avg_ms'] = a.pop('total_ms') / a['count']
        a['cpu_avg_ms'] = a.pop('cpu_total_ms') / a['count']
    return dict(source=str(Path(path).resolve()), axes=axes.pop(), windows=windows, metrics=metrics,
                scope='Nested elapsed and thread CPU phases; do not sum request + dispatch + core')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('log'); p.add_argument('--skip-seconds', type=float, default=10)
    p.add_argument('--output')
    args = p.parse_args()
    result = json.dumps(summarize(args.log, args.skip_seconds), indent=2)
    if args.output: Path(args.output).write_text(result+'\n', encoding='utf-8')
    print(result)


if __name__ == '__main__': main()
