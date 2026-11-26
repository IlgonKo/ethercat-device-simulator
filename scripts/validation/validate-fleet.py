#!/usr/bin/env python3
"""Validate configured C++/Python contracts without opening a physical NIC."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', required=True)
    parser.add_argument('--env-file', help='Environment file (default: project .env); storage is always replaced by a temporary directory')
    parser.add_argument('--timing', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'src'))
    from functional_model.configuration import read_env, load_environment
    with tempfile.TemporaryDirectory(prefix='cmmt-check-') as private:
        folder = Path(private)
        env = read_env(Path(args.env_file) if args.env_file else root/'.env')
        env['DEVICE_SIMULATOR_STATE_DIR'] = str(folder)
        config = load_environment(env)
        socket = folder/'model.sock'; fixture = folder/'fixture'
        with (folder/'model.log').open('w+') as log:
            model = subprocess.Popen([sys.executable, '-m', 'functional_model',
                '--environment',
                '--fixture-dir', str(fixture), '--socket', str(socket)], stdout=log, stderr=log, env={**os.environ, **env, "PYTHONPATH": str(root/"src") + os.pathsep + str(root)})
            try:
                deadline = time.monotonic()+30
                while not socket.exists():
                    if model.poll() is not None or time.monotonic()>deadline:
                        log.seek(0)
                        raise RuntimeError('Model startup failed: '+log.read())
                    time.sleep(.02)
                subprocess.run([str(Path(args.binary).resolve()), '--validate',
                    str(fixture/'cmmt.json'), str(fixture/'contract.json'), str(socket)] + (['--timing'] if args.timing else []),
                    check=True, timeout=30)
                if model.wait(timeout=5) != 0:
                    log.seek(0); raise RuntimeError(log.read())
            finally:
                if model.poll() is None:
                    model.terminate()
                    try: model.wait(timeout=3)
                    except subprocess.TimeoutExpired: model.kill(); model.wait()
    print(f"{len(config['devices'])}-axis C++ ESI/OD and Python IPC contracts validated; no physical NIC opened.")


if __name__ == '__main__': main()
