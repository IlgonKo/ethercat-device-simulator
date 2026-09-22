#!/usr/bin/env python3
"""Own one simulator subprocess for the lifetime of an SSH diagnostic session."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nic', default='enp1s0')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id.isalnum():
        parser.error('run-id must be alphanumeric')
    root = Path(__file__).resolve().parents[2]
    folder = root / 'build' / 'diagnostics' / args.run_id
    folder.mkdir(parents=True, exist_ok=False)
    index = (Path('/sys/class/net') / args.nic / 'ifindex').read_text().strip()

    def sockets():
        rows = Path('/proc/net/packet').read_text().splitlines()[1:]
        return {f[-1] for row in rows if len(f := row.split()) >= 9
                and f[3].lower() == '88a4' and f[4] == index}

    process = None
    result = {'ok': False, 'run_id': args.run_id}
    with (root / 'build' / 'diagnostic-session.lock').open('w') as lock, \
            (folder / 'simulator.log').open('w+') as log:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if sockets():
                raise RuntimeError('EtherCAT socket already active on NIC; stop the existing owner first')
            config = subprocess.check_output(
                [sys.executable, str(root / 'scripts/linux/prepare-board-fixture.py')], text=True).strip()
            process = subprocess.Popen(
                ['bash', str(root / 'scripts/linux/run-simulator.sh'), args.nic],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                env={**os.environ, 'KICKCAT_SLAVE_CONFIG': config})
            deadline = time.monotonic() + 10
            while not sockets():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Simulator did not bind its EtherCAT socket')
                time.sleep(0.1)
            if process.poll() is not None:
                raise RuntimeError('Simulator exited during startup')
            print(json.dumps({'event': 'ready', 'pid': process.pid,
                              'revision': subprocess.check_output(
                                  ['git', '-C', str(root / 'third_party/KickCAT'), 'rev-parse', 'HEAD'],
                                  text=True).strip()}), flush=True)
            selector = selectors.DefaultSelector()
            selector.register(sys.stdin, selectors.EVENT_READ)
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Simulator exited unexpectedly')
                if selector.select(timeout=0.2):
                    command = sys.stdin.readline()
                    if command.strip() == 'stop' or not command:
                        result['ok'] = True
                        break
            else:
                raise RuntimeError('Diagnostic session exceeded 600 seconds')
        except Exception as exc:
            result['error'] = str(exc)
        finally:
            if process is not None:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                result['exit_code'] = process.returncode
                result['ok'] = result['ok'] and process.returncode == 0 and not sockets()
            log.flush()
            log.seek(0)
            result['log'] = log.read()
            print(json.dumps({'event': 'finished', **result}), flush=True)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
