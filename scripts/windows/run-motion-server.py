#!/usr/bin/env python3
"""Run the unchanged Motion Server with isolated RF-004 test configuration."""
import argparse
import _thread
from dataclasses import asdict
import json
from pathlib import Path
import sys
import threading


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--backend',choices=('pysoem','mock'),default='pysoem')
    p.add_argument('--port',type=int,default=15100)
    p.add_argument('--check',action='store_true')
    p.add_argument('--supervised-stdin',action='store_true')
    args=p.parse_args()
    source=Path(args.source).resolve(strict=True)
    sys.path.insert(0,str(source))
    from configuration import ConfigurationSource
    from motion_server.application import MotionServerApplication
    # Read committed examples, never the user's active .env. Pass a dedicated
    # configuration environment rather than inheriting unrelated bench settings.
    environment={
        'MOTION_SERVER_BACKEND':args.backend,
        'MOTION_SERVER_BUS':'cmmt_as',
        'MOTION_SERVER_PORT':str(args.port),
        'MOTION_SERVER_MODE':'basic',
        'MOTION_SERVER_MOTION_MODE':'pp',
        'MOTION_SERVER_CMMT_AXIS_PDO_CONFIGURATIONS':'0:motion_server_default',
        'MOTION_SERVER_CMMT_SLAVE_NON_PDO_CONFIGURATIONS':'0:linear_mm',
        'PYSOEM_INTERFACE':r'\Device\NPF_{906A65C9-C606-4B1F-8384-2625829A4D18}',
        'PYSOEM_CYCLE_TIME':'0.01',
        'PYSOEM_SYNC_MODE':'0',
        'PYSOEM_DC_ENABLED':'0',
        'PYSOEM_DC_PHASE_LOCK':'0',
        'MOTION_SERVER_COMMAND_LOGS':'1',
        'MOTION_SERVER_STATUS_LOGS':'1',
    }
    app=MotionServerApplication.from_source(ConfigurationSource(
        project_root=source,project_filename='.env.example',device_filename='.env.example'),
        environ=environment)
    if app.config is None:raise RuntimeError(str(app.initialization_exception))
    if args.check:
        print(json.dumps(asdict(app.config),default=str,indent=2));return
    if args.supervised_stdin:
        def monitor():
            for line in sys.stdin:
                if line.strip()=='stop':break
            _thread.interrupt_main()
        threading.Thread(target=monitor,daemon=True).start()
    try:app.run()
    except KeyboardInterrupt:pass


if __name__=='__main__':main()
