#!/usr/bin/env python3
"""Aggregate simulator timing windows; never treat these as master WKC measurements."""
import argparse
import json
from pathlib import Path


def summarize(path, skip_seconds=0):
    metrics = {}
    axes = set()
    windows = 0
    failures = 0
    first = last = None
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.startswith('{'): continue
        try: record = json.loads(line)
        except json.JSONDecodeError: continue  # A live writer may have an incomplete final line.
        if record.get('event') != 'simulator-timing': continue
        # Exclude entire windows crossing the requested warmup boundary.
        if record['elapsed_s'] - record['window_s'] < skip_seconds: continue
        axes.add(record['axes']); windows += 1
        failures += record['ipc_failures']
        begin = record['elapsed_s'] - record['window_s']
        first = begin if first is None else min(first, begin)
        last = record['elapsed_s'] if last is None else max(last, record['elapsed_s'])
        for key, value in record['metrics'].items():
            n = value['count']
            if not n: continue
            aggregate = metrics.setdefault(key, dict(count=0, total_ms=0, min_ms=value['min_ms'],
                max_ms=value['max_ms'], over_2ms=0, over_8ms=0))
            aggregate['count'] += n; aggregate['total_ms'] += value['avg_ms'] * n
            aggregate['min_ms'] = min(aggregate['min_ms'], value['min_ms'])
            aggregate['max_ms'] = max(aggregate['max_ms'], value['max_ms'])
            aggregate['over_2ms'] += value['over_2ms']; aggregate['over_8ms'] += value['over_8ms']
    if not windows: raise ValueError('No complete timing windows selected')
    if len(axes) != 1: raise ValueError('Mixed axis counts: use separate logs for each run')
    for value in metrics.values():
        value['avg_ms'] = value.pop('total_ms') / value['count']
    return dict(source=str(Path(path).resolve()), axes=axes.pop(), windows=windows,
                elapsed_span_s=last-first, ipc_failures=failures, metrics=metrics,
                scope='Simulator userspace timing; not wire latency, Python-only compute time, or WKC')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log')
    parser.add_argument('--skip-seconds', type=float, default=0)
    parser.add_argument('--output')
    args = parser.parse_args()
    result = json.dumps(summarize(args.log, args.skip_seconds), indent=2)
    if args.output: Path(args.output).write_text(result+'\n', encoding='utf-8')
    print(result)


if __name__ == '__main__': main()
