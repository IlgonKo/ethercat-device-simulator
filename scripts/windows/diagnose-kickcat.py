#!/usr/bin/env python3
"""Physical Windows PySOEM <-> Linux KickCAT Board diagnostic (not CMMT)."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import queue
import shlex
import subprocess
import threading
import time
import traceback
import uuid

import pysoem
from sdo_checks import run_sdo_checks, run_sdo_error_checks


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter-guid', default='906A65C9-C606-4B1F-8384-2625829A4D18')
    parser.add_argument('--ssh-host', default='Edge-ubuntu')
    parser.add_argument('--remote-repo', default='/home/festo/Documents/ethercat-device-simulator')
    parser.add_argument('--nic', default='enp1s0')
    parser.add_argument('--cycles', type=int, default=1000)
    parser.add_argument('--period-ms', type=float, default=10)
    parser.add_argument('--with-sdo', action='store_true',
                        help='Stage 2-1: PRE-OP SDO checks and assignment restore before PDO regression')
    parser.add_argument('--sdo-errors', action='store_true',
                        help='Additionally require correct SDO aborts (known upstream interoperability failure)')
    args = parser.parse_args()
    if args.sdo_errors and not args.with_sdo:
        parser.error('--sdo-errors requires --with-sdo')
    require(1 <= args.cycles <= 20000 and args.period_ms >= 1
            and args.cycles * args.period_ms < 500000, 'Invalid cycle count/duration')
    run_id = uuid.uuid4().hex
    folder = Path(__file__).resolve().parents[2] / 'build' / 'diagnostics' / run_id
    folder.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', handlers=[
        logging.FileHandler(folder / 'diagnostic.log', encoding='utf-8'), logging.StreamHandler()])
    report = {'run_id': run_id, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'pysoem': pysoem.__version__, 'arguments': vars(args), 'passed': False,
              'stages': {}, 'cleanup_errors': []}
    master = pysoem.Master()
    opened = False
    remote = None
    lines = queue.Queue()
    remote_lines = []
    stage = 'adapter'

    def reader(stream):
        for line in stream:
            remote_lines.append(line)
            lines.put(line)
        lines.put(None)

    def snapshot():
        master.read_state()
        return [{'name': s.name, 'state': s.state, 'al_status': s.al_status,
                 'al_description': pysoem.al_status_code_to_string(s.al_status)}
                for s in master.slaves]

    try:
        adapter = next((a for a in pysoem.find_adapters()
                        if '{' + args.adapter_guid.upper().strip('{}') + '}' in a.name.upper()), None)
        require(adapter is not None, 'Requested Windows NIC not found')
        report['adapter'] = adapter.name
        stage = 'simulator_start'
        command = 'python3 -u ' + shlex.quote(args.remote_repo + '/scripts/linux/diagnostic-session.py')
        command += ' --nic ' + shlex.quote(args.nic) + ' --run-id ' + run_id
        remote = subprocess.Popen(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                                   args.ssh_host, command], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, encoding='utf-8')
        threading.Thread(target=reader, args=(remote.stdout,), daemon=True).start()
        deadline = time.monotonic() + 25
        while True:
            line = lines.get(timeout=max(0.01, deadline - time.monotonic()))
            require(line is not None, 'SSH exited before simulator became ready')
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logging.info('SSH: %s', line.strip())
                continue
            require(event['event'] != 'finished', str(event))
            if event['event'] == 'ready':
                report['simulator'] = event
                break
        logging.info('Simulator ready on %s', args.nic)
        stage = 'discovery'
        master.open(adapter.name)
        opened = True
        count = master.config_init()
        require(count == 1, f'Expected 1 Slave, found {count}')
        slave = master.slaves[0]
        report['identity'] = {'vendor': slave.man, 'product': slave.id, 'revision': slave.rev}
        require((slave.man, slave.id, slave.rev) == (0x6a5, 0xdefede, 0x5a01),
                'Unexpected Slave identity; refusing writes')
        require(master.state_check(pysoem.PREOP_STATE, 2000000) == pysoem.PREOP_STATE,
                'PRE-OP failed')
        report['stages'][stage] = snapshot()
        logging.info('Found Board Slave, PRE-OP reached')
        if args.with_sdo:
            stage = 'sdo'
            run_sdo_checks(slave, report['stages'].setdefault(stage, {}))
            logging.info('SDO reads, Complete Access and write/restore passed')
        if args.sdo_errors:
            stage = 'sdo_errors'
            run_sdo_error_checks(slave, report['stages'].setdefault(stage, {}))
        stage = 'mapping'
        mapped = master.config_map()
        report['stages'][stage] = {'mapped_bytes': mapped, 'inputs': len(slave.input),
                                  'outputs': len(slave.output), 'expected_wkc': master.expected_wkc}
        require((len(slave.input), len(slave.output)) == (12, 3), 'Unexpected PDO lengths')
        require(master.expected_wkc > 0, 'Invalid expected WKC')
        require(master.state_check(pysoem.SAFEOP_STATE, 2000000) == pysoem.SAFEOP_STATE,
                'SAFE-OP failed')
        stage = 'operational'
        slave.output = b'\x55\x33\x11'
        master.send_processdata()
        master.receive_processdata(20000)
        master.state = pysoem.OP_STATE
        master.write_state()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            master.send_processdata()
            master.receive_processdata(20000)
            if master.state_check(pysoem.OP_STATE, 1000) == pysoem.OP_STATE:
                break
            time.sleep(args.period_ms / 1000)
        else:
            raise RuntimeError('OP transition timed out')
        report['stages'][stage] = snapshot()
        logging.info('OP reached; exchanging %d cycles', args.cycles)
        stage = 'cyclic'
        samples = []
        report['stages'][stage] = {'samples': samples}
        period = args.period_ms / 1000
        next_cycle = time.perf_counter()
        start = next_cycle
        for cycle in range(args.cycles):
            slave.output = bytes((cycle % 255, (cycle // 255) % 255, 0x55))
            sent = time.perf_counter()
            master.send_processdata()
            wkc = master.receive_processdata(20000)
            data = slave.input
            samples.append({'cycle': cycle, 'time_ms': (sent - start) * 1000,
                            'wkc': wkc, 'input': data.hex(), 'output': slave.output.hex()})
            require(wkc == master.expected_wkc, f'Cycle {cycle}: WKC {wkc}, expected {master.expected_wkc}')
            require(len(data) == 12 and len(set(data)) == 1 and data[0] % 0x11 == 0,
                    f'Cycle {cycle}: unexpected input pattern {data.hex()}')
            next_cycle += period
            time.sleep(max(0, next_cycle - time.perf_counter()))
        patterns = Counter(s['input'] for s in samples)
        report['stages'][stage]['patterns'] = dict(patterns)
        intervals = [samples[i]['time_ms'] - samples[i - 1]['time_ms']
                     for i in range(1, len(samples))]
        report['stages'][stage]['cycle_intervals_ms'] = {
            'min': min(intervals) if intervals else None,
            'max': max(intervals) if intervals else None,
            'mean': sum(intervals) / len(intervals) if intervals else None}
        require(len(patterns) >= 2, 'Input test pattern did not change')
        final_states = snapshot()
        require(all(s['state'] == pysoem.OP_STATE for s in final_states), 'Slave left OP')
        report['final_states'] = final_states
        report['passed'] = True
        logging.info('PASS: all cycles matched expected WKC; %d input patterns', len(patterns))
    except (Exception, KeyboardInterrupt) as exc:
        report['failed_stage'] = stage
        report['error'] = repr(exc)
        logging.error('FAIL at %s: %s', stage, exc)
        (folder / 'exception.txt').write_text(traceback.format_exc(), encoding='utf-8')
        if opened:
            try:
                report['failure_states'] = snapshot()
            except Exception as state_exc:
                report['state_read_error'] = repr(state_exc)
    finally:
        if opened:
            try:
                master.state = pysoem.INIT_STATE
                master.write_state()
                require(master.state_check(pysoem.INIT_STATE, 2000000) == pysoem.INIT_STATE,
                        'Master cleanup INIT failed')
            except Exception as exc:
                report['cleanup_errors'].append(repr(exc))
            finally:
                try:
                    master.close()
                except Exception as exc:
                    report['cleanup_errors'].append(repr(exc))
        if remote is not None:
            try:
                if remote.poll() is None:
                    remote.stdin.write('stop\n')
                    remote.stdin.flush()
                    remote.stdin.close()
                remote.wait(timeout=15)
                deadline = time.monotonic() + 3
                finished = None
                while time.monotonic() < deadline:
                    line = lines.get(timeout=max(0.01, deadline - time.monotonic()))
                    if line is None:
                        break
                    try:
                        event = json.loads(line)
                        if event.get('event') == 'finished':
                            finished = event
                    except json.JSONDecodeError:
                        pass
                report['remote_cleanup'] = finished
                require(remote.returncode == 0 and finished and finished['ok'], 'Remote cleanup failed')
            except Exception as exc:
                report['cleanup_errors'].append(repr(exc))
                if remote.poll() is None:
                    remote.terminate()
            (folder / 'remote-session.log').write_text(''.join(remote_lines), encoding='utf-8')
        report['passed'] = report['passed'] and not report['cleanup_errors']
        (folder / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        logging.info('Result: %s', folder / 'result.json')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
