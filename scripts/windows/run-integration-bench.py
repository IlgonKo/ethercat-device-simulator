#!/usr/bin/env python3
"""Start the Linux simulator, Windows Motion Server and optional Axis Panel."""
import argparse
import json
import os
import subprocess
import sys
import time
from integration_bench import Bench


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--model-root',default='/home/festo/Documents/ethercat-device-simulator/build/model-source-da0b0a3')
    parser.add_argument('--port',type=int,default=15100)
    parser.add_argument('--panel',action='store_true',help='Open the Axis Control Panel window')
    parser.add_argument('--duration',type=float,default=540,help='Run for 1..540 seconds after startup (default 9 minutes)')
    args=parser.parse_args()
    if not 1 <= args.duration <= 540:parser.error('--duration must be between 1 and 540 seconds')
    bench=Bench(args.source,args.model_root,port=args.port)
    sys.path.insert(0,str(bench.source))
    from control_panel.axis_control_panel.client import AxisServerClient
    probe=AxisServerClient('127.0.0.1',args.port)
    panel=None;panel_log=None;error=None
    try:
        bench.start();probe.start()
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            connected,_,feedback,_,_=probe.get_snapshot()
            if connected and feedback.get('process_data_valid'):break
            if bench.server.poll() is not None:raise RuntimeError('Motion Server exited; inspect log')
            time.sleep(.1)
        else:raise RuntimeError('Motion Server did not produce valid feedback; inspect log')
        probe.stop()
        if args.panel:
            env={**os.environ,'MOTION_SERVER_HOST':'127.0.0.1','MOTION_SERVER_PORT':str(args.port),
                 'AXIS_CONTROL_PANEL_AXIS_NAMES':'CMMT-AS Simulator','AXIS_PANEL_AUTO_SDO_READS':'0'}
            panel_log=(bench.folder/'axis-panel.log').open('w',encoding='utf-8')
            panel=subprocess.Popen([sys.executable,'-u','-m','control_panel.axis_control_panel.control_panel'],
                cwd=bench.source,env=env,stdout=panel_log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        print(f'READY: Axis Panel endpoint 127.0.0.1:{args.port}',flush=True)
        print(f'Auto-stop after {args.duration:g} seconds. Ctrl+C stops this owned bench.',flush=True)
        print(f'Logs: {bench.folder}',flush=True)
        deadline=time.monotonic()+args.duration
        while time.monotonic()<deadline:
            if bench.server.poll() is not None:raise RuntimeError('Motion Server exited')
            if bench.remote.poll() is not None:raise RuntimeError('Linux simulator session ended')
            if panel and panel.poll() is not None:
                if panel.returncode:raise RuntimeError('Axis Panel exited with an error')
                break
            time.sleep(.2)
    except KeyboardInterrupt:pass
    except Exception as exc:
        error=repr(exc);print(error,flush=True)
    finally:
        if probe.thread.is_alive():probe.stop()
        if panel and panel.poll() is None:panel.terminate();panel.wait(timeout=5)
        if panel_log:panel_log.close()
        bench.close()
        (bench.folder/'manual-session.json').write_text(json.dumps({'error':error,'cleanup_errors':bench.cleanup_errors},indent=2),encoding='utf-8')
        print(f'Stopped. Logs: {bench.folder}',flush=True)
    return 1 if error or bench.cleanup_errors else 0


if __name__=='__main__':raise SystemExit(main())
