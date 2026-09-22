#!/usr/bin/env python3
"""Own the CMMT simulator and model service until SSH EOF or explicit stop."""
import argparse
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time


def create_run_folder(parent, run_id):
    """Atomically reserve a new log directory without replacing previous runs."""
    parent.mkdir(parents=True, exist_ok=True)
    attempt = 1
    while True:
        folder = parent / (run_id if attempt == 1 else f'{run_id}-{attempt}')
        try:
            folder.mkdir()
            return folder
        except FileExistsError:
            attempt += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--model-root', required=True)
    parser.add_argument('--nic')
    parser.add_argument('--config')
    parser.add_argument('--timing', action='store_true', help='Record per-second frame and IPC timing')
    parser.add_argument('--binary', help='Explicit simulator executable (default: build/cmmt/cmmt_simulator)')
    parser.add_argument('--timeout', type=int, default=0,
                        help='Maximum session seconds after ready; 0 disables the limit (default)')
    args = parser.parse_args()
    if args.timeout < 0: parser.error('--timeout must be 0 or greater')
    if not args.run_id.isalnum(): parser.error('run-id must be alphanumeric')
    root = Path(__file__).resolve().parents[2]
    if args.config:
        if args.nic: parser.error('--nic and --config are mutually exclusive; NIC comes from JSON')
        sys.path.insert(0, str(root))
        from simulator.configuration import load_config
        config = load_config(args.config)
        args.config = str(Path(args.config).resolve())
        args.nic = config['ethercat']['interface']
    else:
        args.nic = args.nic or 'enp1s0'
    folder = create_run_folder(root / 'build/diagnostics', args.run_id)
    print(json.dumps({'event':'session-created', 'run_id':folder.name,
                      'requested_run_id':args.run_id, 'log_directory':str(folder)}), flush=True)
    index = (Path('/sys/class/net') / args.nic / 'ifindex').read_text().strip()
    def sockets():
        return {f[-1] for row in Path('/proc/net/packet').read_text().splitlines()[1:]
                if len(f := row.split()) >= 9 and f[3].lower() == '88a4' and f[4] == index}
    processes = []
    result = {'event':'finished','ok':False,'run_id':folder.name,
              'requested_run_id':args.run_id,'log_directory':str(folder)}
    with (root/'build/diagnostic-session.lock').open('w') as lock, \
            (folder/'simulator.log').open('w+') as log, \
            (folder/'model.log').open('w+') as model_log, \
            tempfile.TemporaryDirectory(prefix='cmmt-') as private:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if sockets(): raise RuntimeError('EtherCAT NIC already owned by another process')
            ssh = os.environ.get('SSH_CONNECTION','').split()
            if len(ssh)==4:
                local = ipaddress.ip_address(ssh[2].split('%')[0])
                info = json.loads(subprocess.check_output(['ip','-j','addr','show','dev',args.nic]))
                if any(ipaddress.ip_address(a['local'].split('%')[0]) == local for i in info for a in i.get('addr_info',[])):
                    raise RuntimeError('Refusing current SSH interface')
            if (Path('/sys/class/net')/args.nic/'carrier').read_text().strip()!='1':
                raise RuntimeError('EtherCAT NIC has no carrier')
            binary = Path(args.binary).resolve(strict=True) if args.binary else root/'build/cmmt/cmmt_simulator'
            caps = subprocess.check_output(['getcap',str(binary)],text=True)
            if os.geteuid()!=0 and not all(x in caps for x in ('cap_net_raw','cap_net_admin','=ep')):
                raise RuntimeError(f'Missing capabilities: sudo setcap cap_net_raw,cap_net_admin=ep {binary}')
            fixture = folder/'fixture'
            path = str(Path(private)/'model.sock')
            command = [sys.executable, '-u', str(root/'simulator/model_service.py'),
                       '--model-root', args.model_root, '--fixture-dir', str(fixture), '--socket', path]
            if args.config: command += ['--config', args.config]
            if args.timing: command += ['--timing']
            model = subprocess.Popen(command, stdout=model_log, stderr=model_log, start_new_session=True)
            processes.append(model)
            deadline=time.monotonic()+10
            while not Path(path).exists():
                if model.poll() is not None or time.monotonic()>deadline: raise RuntimeError('Model startup failed')
                time.sleep(.05)
            sim_command=[str(binary),args.nic,str(fixture/'cmmt.json'),str(fixture/'contract.json'),path]
            if args.timing: sim_command.append('--timing')
            sim=subprocess.Popen(sim_command,stdout=log,stderr=log,start_new_session=True)
            processes.append(sim)
            deadline=time.monotonic()+10
            while not sockets():
                if any(p.poll() is not None for p in processes) or time.monotonic()>deadline:
                    raise RuntimeError('CMMT simulator startup failed')
                time.sleep(.05)
            spec=json.loads((fixture/'contract.json').read_text())
            print(json.dumps({'event':'ready','pid':sim.pid,'model_pid':model.pid,
                              'contract':spec}),flush=True)
            selector=selectors.DefaultSelector(); selector.register(sys.stdin,selectors.EVENT_READ)
            deadline=time.monotonic()+args.timeout if args.timeout else None
            while deadline is None or time.monotonic()<deadline:
                if any(p.poll() is not None for p in processes):raise RuntimeError('CMMT process exited unexpectedly')
                if selector.select(.1):
                    command=sys.stdin.readline()
                    if not command or command.strip()=='stop':result['ok']=True;break
            else:raise RuntimeError(f'Session exceeded {args.timeout} seconds')
        except KeyboardInterrupt:
            result['ok']=True
        except Exception as exc:
            result['error']=repr(exc)
        finally:
            codes=[]
            for p in reversed(processes):
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                codes.append(p.returncode)
            result['exit_codes_simulator_model']=codes
            result['ok']=result['ok'] and not sockets() and codes[:1]==[0] and all(c in (0,-15) for c in codes)
            log.flush();log.seek(0);result['log']=log.read()
            model_log.flush();model_log.seek(0);result['model_log']=model_log.read()
            print(json.dumps(result),flush=True)
    return 0 if result['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
