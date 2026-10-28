from pathlib import Path
import socket
import os
import json
from functional_model.diagnostics.python_timing import stamp
MAX_MESSAGE = 1024 * 1024

def dispatch_request(model, request):
    # Axis runtime projects cycle failures as explicit Fault feedback.
    if request.get('op') not in ('read', 'write'):
        return model.dispatch(request)
    from functional_model.cia402_drive.adapter.errors import DeviceRejectedException, SdoObjectNotFoundException
    try:
        return model.dispatch(request)
    except (DeviceRejectedException, SdoObjectNotFoundException, KeyError, ValueError) as exc:
        if isinstance(exc, DeviceRejectedException): code = 0x06010000
        elif isinstance(exc, (SdoObjectNotFoundException, KeyError)): code = 0x06020000
        else: code = 0x06090030
        return {'error': {'kind': 'sdo_abort', 'code': code, 'message': str(exc)}}
    except OSError as exc:
        return {'error': {'kind': 'sdo_abort', 'code': 0x08000020, 'message': str(exc)}}


def serve(model, path, timing=None):
    # Caller supplies a private session directory; never unlink an existing socket.
    path=Path(path)
    if path.exists(): raise FileExistsError(path)
    if path.parent.stat().st_mode & 0o077: raise ValueError('Socket directory must have mode 0700')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(path)); os.chmod(path,0o600); server.listen(1); server.settimeout(30)
        print(json.dumps({'event':'model-ready','socket':str(path)}),flush=True)
        try:
            conn,_=server.accept()
            with conn,conn.makefile('rwb') as stream:
                # The owning session bounds lifetime; an idle EtherCAT link is
                # not by itself an IPC failure. Client RPC deadline is bounded.
                conn.settimeout(None)
                while True:
                    raw=stream.readline(MAX_MESSAGE+1)
                    if not raw: break
                    if len(raw)>MAX_MESSAGE or not raw.endswith(b'\n'): raise ValueError('Invalid IPC message length')
                    # Fail closed: no successful SDO/PDO response after a model exception.
                    if timing:
                        begin = stamp()
                        request = json.loads(raw)
                        after_parse = stamp()
                        response = dispatch_request(model, request)
                        after_dispatch = stamp()
                        encoded = json.dumps(response,separators=(',',':')).encode()+b'\n'
                        after_encode = stamp()
                        stream.write(encoded); stream.flush()
                        after_send = stamp()
                        op = request['op']
                        timing.add(op+'_json_decode', begin, after_parse)
                        timing.add(op+'_dispatch', after_parse, after_dispatch)
                        timing.add(op+'_json_encode', after_dispatch, after_encode)
                        timing.add(op+'_send', after_encode, after_send)
                        timing.add(op+'_request', begin, after_send)
                        timing.due()
                    else:
                        response=dispatch_request(model, json.loads(raw))
                        stream.write(json.dumps(response,separators=(',',':')).encode()+b'\n'); stream.flush()
        finally:
            if timing: timing.flush("stop")
            path.unlink(missing_ok=True)


