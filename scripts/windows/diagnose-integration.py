#!/usr/bin/env python3
"""Exercise the existing Axis Panel client and GUI against the real Motion Server."""
import argparse
import json
import sys
import time
import traceback
from integration_bench import Bench


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--model-root',default='/home/festo/Documents/ethercat-device-simulator/build/model-source-da0b0a3')
    p.add_argument('--backend',choices=('pysoem','mock'),default='pysoem')
    p.add_argument('--port',type=int,default=15100)
    p.add_argument('--smoke',action='store_true')
    args=p.parse_args()
    bench=Bench(args.source,args.model_root,args.backend,args.port)
    sys.path.insert(0,str(bench.source))
    from control_panel.axis_control_panel.client import AxisServerClient
    class ObservedPanelClient(AxisServerClient):
        def __init__(self,*values):
            super().__init__(*values)
            self.diagnostic_messages=[]
        def _store_diagnosis_result(self,message):
            self.diagnostic_messages.append(dict(message))
            super()._store_diagnosis_result(message)
    client=ObservedPanelClient('127.0.0.1',args.port)
    panel=None;stage='startup';report={'backend':args.backend,'passed':False,'stages':{}}
    def snapshot():
        if panel:panel.root.update()
        connected,error,feedback,notice,diagnosis=client.get_snapshot()
        if notice:report.setdefault('notices',[]).append(notice)
        if diagnosis:report.setdefault('diagnoses',[]).append(diagnosis)
        report['last_feedback']=feedback
        if bench.server and bench.server.poll() is not None:raise RuntimeError('Motion Server exited')
        return feedback
    def wait(predicate,seconds=10):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            f=snapshot()
            if predicate(f):report['stages'][stage]=f;return f
            time.sleep(.025)
        raise RuntimeError(f'Timeout at {stage}; inspect motion-server.log and last_feedback')
    try:
        bench.start();client.start()
        wait(lambda f:f.get('process_data_valid') and len(f.get('actual_positions',[]))==1,20)
        print(f'{args.backend}: Motion Server ready; Axis Panel client has one axis',flush=True)
        if not args.smoke:
            from control_panel.axis_control_panel.control_panel import AxisServerControlPanel
            from tkinter import messagebox
            # A GUI error must fail the test rather than leave a blocking dialog.
            def gui_error(title,message):raise RuntimeError(f'{title}: {message}')
            messagebox.showerror=gui_error
            panel=AxisServerControlPanel(client,['CMMT-AS Simulator'],False)
            panel.root.withdraw()
            stage='panel_status'
            wait(lambda f:panel.process_data_valid and panel.latest_axis_metadata[0].get('position_unit')=='mm')
            stage='authority';panel.toggle_command_authority()
            wait(lambda f:f.get('command_authority',{}).get('owned_by_this_client'))
            # Motion Server initialization already enables the drive. Establish
            # disabled feedback before exercising the Panel's toggle button.
            stage='initial_disable';client.send_axis_disable(0)
            wait(lambda f:f['statuswords'][0]&0x6f==0x23 and not panel.selected_axis_operation_enabled)
            stage='enable';panel.toggle_axis_enable()
            wait(lambda f:f['statuswords'][0]&0x6f==0x27 and panel.selected_axis_operation_enabled)
            stage='homing';panel.homing_start()
            wait(lambda f:bool(f['statuswords'][0]&0x8000))
            stage='move'
            client.send_axis_move_absolute(0,10.0,100.0)
            f=wait(lambda f:abs(f['actual_positions'][0]-10.0)<.05,15)
            report['move_position']=f['actual_positions'][0]
            stage='panel_display'
            wait(lambda f:abs(float(panel.actual_position_var.get())-10.0)<.05)
            report['panel_position']=panel.actual_position_var.get()
            stage='moving_before_stop';client.send_axis_move_absolute(0,100.0,100.0)
            wait(lambda f:f['actual_positions'][0]>11.0)
            stage='stop';panel.axis_stop()
            f=wait(lambda f:abs(f['actual_velocities'][0])<.01)
            if f['actual_positions'][0]>=99:raise RuntimeError('Stop did not interrupt the move')
            report['stopped_position']=f['actual_positions'][0]
            stage='fault_reset';panel.axis_fault_reset()
            wait(lambda f:any(d.get('type')=='system/axis/fault_reset' and d.get('ok') is True
                              for d in client.diagnostic_messages) and f['statuswords'][0]&0x6f==0x23)
            stage='disable';client.send_axis_disable(0)
            wait(lambda f:f['statuswords'][0]&0x6f==0x23)
        report['passed']=True
        print(f'{args.backend}: PASS {stage}',flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        report.update(error=repr(exc),failed_stage=stage)
        (bench.folder/'exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
        print(f'{args.backend}: FAIL {stage}: {exc}',flush=True)
    finally:
        if panel:panel.root.destroy()
        if client.thread.is_alive():client.stop()
        bench.close()
        report['cleanup_errors']=bench.cleanup_errors
        report['diagnostic_messages']=client.diagnostic_messages
        report['passed']=report['passed'] and not bench.cleanup_errors
        (bench.folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Result: {bench.folder}',flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
