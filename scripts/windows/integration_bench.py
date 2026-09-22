"""Owned subprocesses shared by RF-004 diagnostics and the manual bench launcher."""
import json
import os
from pathlib import Path
import queue
import shlex
import socket
import subprocess
import sys
import threading
import uuid


class Bench:
    def __init__(self, source, model_root, backend='pysoem', port=15100):
        self.source=Path(source).resolve(strict=True)
        self.model_root=model_root;self.backend=backend;self.port=port
        self.root=Path(__file__).resolve().parents[2]
        self.run_id=uuid.uuid4().hex
        self.folder=self.root/'build/integration'/self.run_id
        self.folder.mkdir(parents=True)
        self.remote=None;self.server=None;self.server_log=None
        self.events=queue.Queue();self.remote_lines=[];self.cleanup_errors=[]
        self.remote_cleanup=None

    def start(self):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',self.port))==0:
                raise RuntimeError(f'TCP port {self.port} already in use; existing server left untouched')
        if self.backend=='pysoem':
            command=shlex.join(['python3','-u','/home/festo/Documents/ethercat-device-simulator/scripts/linux/cmmt-session.py',
                               '--run-id',self.run_id,'--nic','enp1s0','--model-root',self.model_root,'--timeout','600'])
            self.remote=subprocess.Popen(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=10','Edge-ubuntu',command],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8')
            def reader():
                for line in self.remote.stdout:
                    self.remote_lines.append(line)
                    try:self.events.put(json.loads(line))
                    except json.JSONDecodeError:pass
                self.events.put(None)
            threading.Thread(target=reader,daemon=True).start()
            ready=self.events.get(timeout=40)
            if not ready or ready.get('event')!='ready':raise RuntimeError(str(ready))
            (self.folder/'simulator-ready.json').write_text(json.dumps(ready,indent=2),encoding='utf-8')
        self.server_log=(self.folder/'motion-server.log').open('w',encoding='utf-8')
        self.server=subprocess.Popen([sys.executable,'-u',str(self.root/'scripts/windows/run-motion-server.py'),
            '--source',str(self.source),'--backend',self.backend,'--port',str(self.port),'--supervised-stdin'],
            stdin=subprocess.PIPE,stdout=self.server_log,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',cwd=self.source,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        return self

    def close(self):
        if self.server:
            try:
                if self.server.poll() is None:
                    self.server.stdin.write('stop\n');self.server.stdin.flush();self.server.stdin.close()
                self.server.wait(timeout=15)
                if self.server.returncode!=0:self.cleanup_errors.append(f'Motion Server exit {self.server.returncode}')
            except Exception as exc:
                self.cleanup_errors.append(repr(exc))
                if self.server.poll() is None:self.server.terminate();self.server.wait(timeout=5)
        if self.server_log:self.server_log.close()
        if self.remote:
            try:
                if self.remote.poll() is None:
                    self.remote.stdin.write('stop\n');self.remote.stdin.flush();self.remote.stdin.close()
                self.remote.wait(timeout=15)
                while True:
                    item=self.events.get(timeout=3)
                    if item is None:break
                    if item.get('event')=='finished':self.remote_cleanup=item
                if self.remote.returncode!=0 or not self.remote_cleanup or not self.remote_cleanup['ok']:
                    self.cleanup_errors.append('Remote cleanup failed')
            except Exception as exc:
                self.cleanup_errors.append(repr(exc))
                if self.remote.poll() is None:self.remote.terminate();self.remote.wait(timeout=5)
        (self.folder/'remote-session.log').write_text(''.join(self.remote_lines),encoding='utf-8')
        (self.folder/'cleanup.json').write_text(json.dumps({'errors':self.cleanup_errors,'remote':self.remote_cleanup},indent=2),encoding='utf-8')
