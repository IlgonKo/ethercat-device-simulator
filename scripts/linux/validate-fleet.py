#!/usr/bin/env python3
"""Validate configured C++/Python contracts without opening a physical NIC."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-root', required=True)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--config', help='Config template; storage is always replaced by a temporary directory')
    parser.add_argument('--timing', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cmmt-check-') as private:
        folder = Path(private)
        config = json.loads((Path(args.config) if args.config else root/'config/four-axes.json').read_text())
        config['storage']['directory'] = str(folder/'parameters')
        path = folder/'config.json'; path.write_text(json.dumps(config))
        socket = folder/'model.sock'; fixture = folder/'fixture'
        with (folder/'model.log').open('w+') as log:
            model = subprocess.Popen([sys.executable, str(root/'simulator/model_service.py'),
                '--model-root', args.model_root, '--config', str(path),
                '--fixture-dir', str(fixture), '--socket', str(socket)], stdout=log, stderr=log)
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
