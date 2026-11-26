# NIC-free Slave + functional-model IPC and persistence integration test.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zlib
ROOT = Path(__file__).resolve().parents[2]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', default='build/timing/cmmt_simulator')
    parser.add_argument('--axes', type=int, choices=(1,2,4), default=1)
    parser.add_argument('--fmu-dir')
    parser.add_argument('--storage-startup', action='store_true')
    parser.add_argument('--motion', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rf014-') as folder:
        root = Path(folder)
        os.chmod(root, 0o700)
        env = dict(os.environ, PYTHONPATH=str(ROOT/'src')+':'+str(ROOT),
                   DEVICE_SIMULATOR_STATE_DIR=str(root/'state'))
        settings = dict(KICKCAT_INTERFACE='unused', DEVICE_SIMULATOR_STATE_DIR=str(root/'state'),
            DEVICE_SIMULATOR_BUS=','.join(f'{i}:axis:cia402-drive' for i in range(args.axes)))
        models=['copley_drive_sim' if args.fmu_dir and i >= args.axes//2 else 'f_kr_cmmt' for i in range(args.axes)]
        for key, values in [('NAMES',[f'axis-{i}' for i in range(args.axes)]), ('MODELS',models),
                            ('MODES',['linear']*args.axes)]:
            settings['DEVICE_SIMULATOR_AXIS_'+key]=','.join(f'{i}:{v}' for i,v in enumerate(values))
        settings['DEVICE_SIMULATOR_FMU_DIR']=str(Path(args.fmu_dir).resolve() if args.fmu_dir else ROOT/'model_artifacts')
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
                    parameters = {p:p.read_bytes() for p in (root/'state').glob('*.json')}
                    subprocess.run([str((ROOT/args.binary).resolve()), '--motion-self-test' if args.motion else '--self-test',
                        str(fixture/'cmmt.json'), str(fixture/'contract.json'), str(sock)],
                        check=True, env=env, cwd=ROOT, timeout=30)
                    assert all(p.read_bytes() == data for p, data in parameters.items()), 'Mapping test changed parameter files'
                    if args.storage_startup and attempt == 1:
                        files = sorted((root/'state'/'pdo-mappings').glob('*.json'))
                        originals = {p:p.read_bytes() for p in files}
                        for kind in ('schema', 'checksum', 'logical'):
                            try:
                                bad = json.loads(originals[files[0]])
                                del bad['checksum']
                                if kind == 'schema': bad['schema_version'] = 999
                                if kind == 'logical': bad['rx'] = [8]
                                canonical = json.dumps(bad, sort_keys=True, separators=(',', ':')).encode()
                                bad['checksum'] = zlib.crc32(canonical)
                                if kind == 'checksum': bad['checksum'] ^= 1
                                files[0].write_text(json.dumps(bad))
                                damaged = files[0].read_bytes()
                                # Model Host intentionally serves one Slave session only.
                                model.wait(timeout=5)
                                fixture = root/f'fixture-startup-{kind}'
                                sock = root/f'model-startup-{kind}.sock'
                                model = subprocess.Popen([sys.executable, '-m', 'functional_model',
                                    '--env-file', str(envfile), '--fixture-dir', str(fixture),
                                    '--socket', str(sock)], env=env, cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
                                for _ in range(200):
                                    if sock.exists(): break
                                    if model.poll() is not None: raise RuntimeError('Model startup failed')
                                    time.sleep(.05)
                                else: raise TimeoutError('Model socket startup')
                                mode = '--self-test' if kind == 'logical' else '--validate'
                                result = subprocess.run([str((ROOT/args.binary).resolve()), mode,
                                    str(fixture/'cmmt.json'), str(fixture/'contract.json'), str(sock)],
                                    env=env, cwd=ROOT, timeout=30, capture_output=True, text=True)
                                if kind == 'logical':
                                    assert result.returncode == 0, result.stderr
                                    assert 'PDO_MAPPING_RESTORE_INVALID' in result.stderr
                                    assert 'DYNAMIC_MAPPING_SELF_TEST' in result.stdout
                                else:
                                    assert result.returncode != 0
                                    assert 'Incompatible or corrupt mapping file' in result.stderr, result.stderr
                                    assert files[0].read_bytes() == damaged
                                print(f'STORAGE_STARTUP case={kind} passed')
                            finally:
                                for path, content in originals.items(): path.write_bytes(content)
                except Exception:
                    log.seek(0);print(log.read());raise
                finally:
                    if model.poll() is None: model.terminate()
                    model.wait(timeout=5)
        files = list((root/'state'/'pdo-mappings').glob('*.json'))
        assert len(files)==args.axes
        saved=json.loads(files[0].read_text())
        assert saved['rx']==[8,0x60400010]
        if args.motion:
            for i in range(args.axes):
                path=root/'state'/'pdo-mappings'/((f'axis-{i}'.encode().hex())+'.json')
                assert json.loads(path.read_text())['tx']==[8*(i+1),0x60410010,0x60640020]
        else:
            assert saved['tx']==[0x60640020,0x60410010,8]
        print('Slave/OD IPC, remap, omitted SDO value and restart persistence passed')
if __name__ == '__main__': main()
