# NIC-free Slave + functional-model IPC and persistence integration test.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parents[2]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', default='build/timing/cmmt_simulator')
    parser.add_argument('--axes', type=int, choices=(1,2,4), default=1)
    parser.add_argument('--fmu-dir')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rf014-') as folder:
        root = Path(folder)
        os.chmod(root, 0o700)
        env = dict(os.environ, PYTHONPATH=str(ROOT/'src')+':'+str(ROOT),
                   DEVICE_SIMULATOR_STATE_DIR=str(root/'state'))
        settings = dict(KICKCAT_INTERFACE='unused', DEVICE_SIMULATOR_STATE_DIR=str(root/'state'),
            DEVICE_SIMULATOR_BUS=','.join(f'{i}:axis:cia402-drive' for i in range(args.axes)))
        models=['copley_drive_sim' if args.fmu_dir and i >= args.axes//2 else 'f_kr_cmmt' for i in range(args.axes)]
        for key, values in [('IDS',[f'axis-{i}' for i in range(args.axes)]), ('MODELS',models),
                            ('MODES',['linear']*args.axes), ('PARAMETER_SETS',[f'axis-{i}' for i in range(args.axes)])]:
            settings['DEVICE_SIMULATOR_AXIS_'+key]=','.join(f'{i}:{v}' for i,v in enumerate(values))
        if args.fmu_dir: settings['DEVICE_SIMULATOR_FMU_DIR']=str(Path(args.fmu_dir).resolve())
        envfile=root/'test.env'
        envfile.write_text('\n'.join(f'{k}={v}' for k,v in settings.items()))
        for attempt in range(2):
            fixture, sock = root/f'fixture-{attempt}', root/f'model-{attempt}.sock'
            with (root/f'model-{attempt}.log').open('w+') as log:
                model = subprocess.Popen([sys.executable, '-m', 'functional_model',
                    '--env-file', str(envfile), '--fixture-dir', str(fixture), '--socket', str(sock)], env=env, cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT)
                try:
                    for _ in range(200):
                        if sock.exists(): break
                        if model.poll() is not None: raise RuntimeError('Model failed to start')
                        time.sleep(.05)
                    else: raise TimeoutError('Model socket startup')
                    subprocess.run([str((ROOT/args.binary).resolve()), '--self-test',
                        str(fixture/'cmmt.json'), str(fixture/'contract.json'), str(sock)],
                        check=True, env=env, cwd=ROOT, timeout=30)
                except Exception:
                    log.seek(0);print(log.read());raise
                finally:
                    if model.poll() is None: model.terminate()
                    model.wait(timeout=5)
        files = list((root/'state'/'pdo-mappings').glob('*.json'))
        assert len(files)==args.axes
        saved=json.loads(files[0].read_text())
        assert saved['rx']==[8,0x60400010]
        assert saved['tx']==[0x60640020,0x60410010,8]
        print('Slave/OD IPC, remap, omitted SDO value and restart persistence passed')
if __name__ == '__main__': main()
