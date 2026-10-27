#!/usr/bin/env python3
"""Offline before/after model CPU benchmark. Does not open an EtherCAT NIC."""
import argparse
import json
from pathlib import Path
import struct
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from functional_model.runtime import axis as model_service
from functional_model.cia402_drive.adapter import f_kr_cmmt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error('iterations must be positive')
    result = {'iterations': args.iterations, 'scope': 'Offline PP enabled at rest; no NIC', 'runs': {}}
    outputs = []
    for enabled in (False, True):
        if enabled:
            model = model_service.Model()
        else:
            with patch.object(f_kr_cmmt, 'install_role_index'):
                model = model_service.Model()
        for cw in (6, 7, 15):
            model.adapter.bridge.rxpdo_payload_to_od(struct.pack('<HbiIihihB', cw, 1, 0, 100, 0, 0, 0, 0, 0))
            model.adapter.model.model_update()
        model.adapter.model.cycle_time = .008
        started = time.perf_counter()
        cpu = time.thread_time()
        for _ in range(args.iterations):
            model.adapter.model.model_update()
        cpu_s = time.thread_time() - cpu
        elapsed_s = time.perf_counter() - started
        result['runs']['indexed' if enabled else 'original'] = {
            'elapsed_s': elapsed_s, 'cpu_s': cpu_s,
            'avg_ms': elapsed_s * 1000 / args.iterations,
            'od_entries': len(model.adapter.model.od.entries),
            'model_source_hash': model.source_hash,
        }
        outputs.append([(key, entry.value) for key, entry in model.adapter.model.od.entries.items()])
    result['final_od_values_equal'] = outputs[0] == outputs[1]
    payload = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(payload + '\n', encoding='utf-8')
    print(payload)
    return 0 if result['final_od_values_equal'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
