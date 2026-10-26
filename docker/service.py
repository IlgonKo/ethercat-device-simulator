"""Non-interactive container supervisor for the existing two-process runtime."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from functional_model.configuration import load_environment

RUN = Path('/run/simulator')
STATE = Path('/state')
STATUS = RUN / 'status.json'


def settings(env):
    nic = env.get('KICKCAT_INTERFACE', '')
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', nic):
        raise ValueError('KICKCAT_INTERFACE must name a dedicated Linux EtherCAT NIC')
    timing = env.get('DEVICE_SIMULATOR_CYCLE_STATS_LOGS', 'false').lower()
    if timing not in ('true', 'false', '1', '0'):
        raise ValueError('DEVICE_SIMULATOR_CYCLE_STATS_LOGS must be true/false or 1/0')
    timeout = int(env.get('DEVICE_SIMULATOR_SESSION_TIMEOUT', '0'))
    if timeout < 0:
        raise ValueError('DEVICE_SIMULATOR_SESSION_TIMEOUT must be >= 0')
    run_id = env.get('DEVICE_SIMULATOR_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', run_id):
        raise ValueError('DEVICE_SIMULATOR_RUN_ID must contain 1-64 letters, digits, _ or -')
    return nic, timing in ('true', '1'), timeout, run_id


def packet_owners(nic):
    index = (Path('/sys/class/net') / nic / 'ifindex').read_text().strip()
    owners = set()
    for row in Path('/proc/net/packet').read_text().splitlines()[1:]:
        fields = row.split()
        if len(fields) >= 9 and fields[3].lower() == '88a4' and fields[4] == index:
            owners.add(fields[-1])
    return owners


def check_nic(nic):
    path = Path('/sys/class/net') / nic
    if not path.exists() or nic == 'lo':
        raise ValueError(f'Invalid EtherCAT NIC: {nic}')
    # A container does not inherit SSH_CONNECTION. Protect default-route NICs; address presence alone is not a rejection reason.
    for line in Path('/proc/net/route').read_text().splitlines()[1:]:
        fields = line.split()
        if fields[0] == nic and fields[1] == '00000000' and int(fields[3], 16) & 1:
            raise ValueError('Refusing default-route NIC; select a dedicated EtherCAT port')
    ipv6 = Path('/proc/net/ipv6_route')
    if ipv6.exists():
        for line in ipv6.read_text().splitlines():
            fields = line.split()
            if fields[-1] == nic and fields[0] == '0' * 32 and fields[1] == '00':
                raise ValueError('Refusing IPv6 default-route NIC')
    if (path / 'carrier').read_text().strip() != '1':
        raise ValueError('EtherCAT NIC has no carrier')
    if packet_owners(nic):
        raise ValueError('EtherCAT NIC already owned by another process')


def write_status(event, processes, **extra):
    value = dict(event=event, time=time.time(),
                 processes={name: dict(pid=p.pid, exit_code=p.poll())
                            for name, p in processes.items()}, **extra)
    temporary = STATUS.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(STATUS)
    if event != 'ready':
        print(json.dumps(value), flush=True)


def healthcheck():
    try:
        status = json.loads(STATUS.read_text())
        if status['event'] != 'ready' or time.time() - status['time'] > 10:
            return 1
        for item in status['processes'].values():
            os.kill(item['pid'], 0)
        return 0
    except (OSError, ValueError, KeyError):
        return 1


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def main():
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--healthcheck', action='store_true')
    parser.add_argument('--validate-only', action='store_true',
                        help='Validate configuration and generate model fixtures without NIC access')
    args = parser.parse_args()
    if args.healthcheck:
        return healthcheck()
    RUN.mkdir(parents=True, exist_ok=True)
    os.chmod(RUN, 0o700)
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    processes = {}
    result = 0
    lock = None
    try:
        nic, timing, timeout, run_id = settings(os.environ)
        STATE.mkdir(parents=True, exist_ok=True)
        lock = (STATE / '.service.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = load_environment(os.environ)
        if Path(config['storage']['directory']) != STATE:
            raise ValueError('Container DEVICE_SIMULATOR_STATE_DIR must be /state')
        if not args.validate_only:
            check_nic(nic)
        fixture = RUN / 'fixture'
        model_command = [sys.executable, '-u', '-m', 'functional_model',
                         '--environment',
                         '--fixture-dir', str(fixture)]
        if timing:
            model_command.append('--timing')
        if not args.validate_only:
            model_command += ['--socket', str(RUN / 'model.sock')]
        print(json.dumps(dict(event='starting', run_id=run_id, interface=nic,
                              timing=timing, timeout_seconds=timeout)), flush=True)
        processes['model'] = subprocess.Popen(model_command)
        deadline = time.monotonic() + 20
        while not stopping:
            code = processes['model'].poll()
            if args.validate_only and code is not None:
                if code != 0:
                    raise RuntimeError(f'Model validation failed: {code}')
                write_status('validated', processes)
                return 0
            if code is not None:
                raise RuntimeError(f'Model startup failed: {code}')
            if not args.validate_only and (RUN / 'model.sock').exists():
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Model startup timeout')
            time.sleep(.05)
        if stopping:
            return 0
        command = [str(ROOT / 'bin/cmmt_simulator'), nic, str(fixture / 'cmmt.json'),
                   str(fixture / 'contract.json'), str(RUN / 'model.sock')]
        if timing:
            command.append('--timing')
        processes['slave'] = subprocess.Popen(command)
        deadline = time.monotonic() + 10
        while not stopping and not packet_owners(nic):
            if any(p.poll() is not None for p in processes.values()):
                raise RuntimeError('Child exited during Slave startup')
            if time.monotonic() > deadline:
                raise RuntimeError('Slave startup timeout')
            time.sleep(.05)
        started = time.monotonic()
        print(json.dumps(dict(event='ready', run_id=run_id)), flush=True)
        while not stopping:
            if processes['slave'].poll() is not None:
                raise RuntimeError(f'Slave exited: {processes["slave"].returncode}')
            if processes['model'].poll() is not None:
                # Do not terminate a surviving Slave just because the Host died.
                # The current C++ client still exits on IPC failure; see RF-012.
                if not (STATUS.exists() and json.loads(STATUS.read_text())['event'] == 'model-failed'):
                    write_status('model-failed', processes)
            else:
                write_status('ready', processes)
            if timeout and time.monotonic() - started >= timeout:
                raise RuntimeError('Configured diagnostic timeout reached')
            time.sleep(.1)
    except Exception as exc:
        result = 1
        write_status('failed', processes, error=str(exc))
    finally:
        for process in reversed(list(processes.values())):
            stop_process(process)
        (RUN / 'model.sock').unlink(missing_ok=True)
        if lock is not None:
            lock.close()
        if not args.validate_only or result:
            write_status('stopped' if result == 0 else 'failed', processes)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
