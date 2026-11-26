# NIC-free production response pump and SAFE-OP ordering barrier tests.
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
ROOT = Path(__file__).resolve().parents[2]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', default='build/timing/cmmt_simulator')
    parser.add_argument('--fmu-dir')
    args = parser.parse_args()
    for case in ('delay', 'timeout', 'stop', 'terminate', 'stale-session', 'stale-request', 'inactive-timeout', 'inactive-stop'):
        with tempfile.TemporaryDirectory(prefix='rf014-ipc-') as directory:
            root = Path(directory)
            env = dict(os.environ, PYTHONPATH=str(ROOT/'src')+':'+str(ROOT),
                       DEVICE_SIMULATOR_STATE_DIR=str(root/'state'), DEVICE_SIMULATOR_MODEL_TIMEOUT_MS='100')
            settings = dict(KICKCAT_INTERFACE='unused', DEVICE_SIMULATOR_STATE_DIR=str(root/'state'),
                            DEVICE_SIMULATOR_BUS=','.join(f'{i}:axis:cia402-drive' for i in range(4)))
            for key, values in (
                ('NAMES', [f'axis-{i}' for i in range(4)]),
                ('MODELS', ['copley_drive_sim' if args.fmu_dir and i < 2 else 'f_kr_cmmt' for i in range(4)]),
                ('MODES', ['linear']*4)):
                settings['DEVICE_SIMULATOR_AXIS_'+key] = ','.join(f'{i}:{v}' for i,v in enumerate(values))
            if args.fmu_dir: settings['DEVICE_SIMULATOR_FMU_DIR'] = str(Path(args.fmu_dir).resolve())
            envfile = root/'test.env'
            envfile.write_text('\n'.join(f'{k}={v}' for k,v in settings.items()))
            fixture, model_socket, proxy_socket = root/'fixture', root/'model.sock', root/'proxy.sock'
            with (root/'model.log').open('w+') as log:
                model = subprocess.Popen([sys.executable, '-m', 'functional_model', '--env-file', str(envfile),
                    '--fixture-dir', str(fixture), '--socket', str(model_socket)], cwd=ROOT, env=env,
                    stdout=log, stderr=subprocess.STDOUT)
                errors = []
                worker = None
                try:
                    for _ in range(200):
                        if model_socket.exists(): break
                        if model.poll() is not None: raise RuntimeError('Model startup failed')
                        time.sleep(.05)
                    else: raise TimeoutError('Model socket startup')
                    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    listener.bind(str(proxy_socket)); listener.listen(1); listener.settimeout(5)
                    def proxy():
                        try:
                            with listener, listener.accept()[0] as client, socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as upstream:
                                upstream.settimeout(2); upstream.connect(str(model_socket))
                                with client.makefile('rwb') as incoming, upstream.makefile('rwb') as outgoing:
                                    exchanges = 0
                                    while raw := incoming.readline():
                                        request = json.loads(raw)
                                        exchange = request['op'] == 'exchange'
                                        if exchange: exchanges += 1
                                        inject = exchange and (not case.startswith('inactive-') or exchanges == 2)
                                        effect = case.removeprefix('inactive-')
                                        if inject and effect == 'stop':
                                            model.send_signal(signal.SIGSTOP)
                                            time.sleep(.25)
                                            model.send_signal(signal.SIGCONT)
                                        if inject and effect == 'terminate':
                                            model.kill(); model.wait(timeout=2); return
                                        outgoing.write(raw); outgoing.flush()
                                        response = json.loads(outgoing.readline())
                                        if inject:
                                            if effect == 'delay': time.sleep(.025)
                                            if effect == 'timeout': time.sleep(.2)
                                            if effect == 'stale-session': response['session'] = 'previous-session'
                                            if effect == 'stale-request': response['request_id'] -= 1
                                            if effect != 'delay':
                                                for value in response['values']:
                                                    if value['index'] == 0x6064: value['data'] = '78563412'
                                        incoming.write(json.dumps(response).encode()+b'\n'); incoming.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                        except Exception as exc:
                            errors.append(exc)
                    worker = threading.Thread(target=proxy)
                    worker.start()
                    result = subprocess.run([str((ROOT/args.binary).resolve()), '--ipc-self-test-'+case,
                        str(fixture/'cmmt.json'), str(fixture/'contract.json'), str(proxy_socket)],
                        cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
                    assert result.returncode == 0, result.stdout+'\n'+result.stderr
                    assert 'IPC_REMAP_TEST' in result.stdout
                    if case != 'delay': assert '"restart_required":true' in result.stderr
                    print(next(line for line in result.stdout.splitlines() if line.startswith('IPC_REMAP_TEST')), flush=True)
                except Exception:
                    log.seek(0); print(log.read()); raise
                finally:
                    if model.poll() is None:
                        model.send_signal(signal.SIGCONT); model.terminate()
                    model.wait(timeout=5)
                    if worker:
                        worker.join(timeout=5)
                        assert not worker.is_alive(), 'Proxy did not terminate'
                assert not errors, errors
if __name__ == '__main__': main()
