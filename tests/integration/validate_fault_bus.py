"""Opt-in isolated Docker/veth test. Never uses the configured hardware NIC or store.

Requires Linux, NET_ADMIN/NET_RAW, pyroute2 and pysoem in a --network none container.
"""
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time

import pysoem
from pyroute2 import IPRoute


def check(condition, detail):
    if not condition:
        raise AssertionError(detail)


def main():
    # Refuse host-network execution: only a pristine private namespace is allowed.
    check(set(os.listdir('/sys/class/net')) == {'lo'}, 'Use Docker --network none')
    with IPRoute() as ip:
        ip.link('add', ifname='fault-master', kind='veth', peer='fault-slave')
        for name in ('fault-master', 'fault-slave'):
            ip.link('set', index=ip.link_lookup(ifname=name)[0], state='up')
    for failure in ('timeout', 'disconnect'):
        with tempfile.TemporaryDirectory(prefix='fault-bus-') as private:
            root = Path(private)
            env = {**os.environ, 'KICKCAT_INTERFACE': 'fault-slave',
                   'DEVICE_SIMULATOR_STATE_DIR': str(root / 'state'),
                   'DEVICE_SIMULATOR_FMU_DIR': '/model_artifacts',
                   'DEVICE_SIMULATOR_BUS': ','.join(f'{i}:axis:cia402-drive' for i in range(4)),
                   'DEVICE_SIMULATOR_AXIS_IDS': ','.join(f'{i}:test-{i}' for i in range(4)),
                   'DEVICE_SIMULATOR_AXIS_MODELS': '0:f_kr_cmmt,1:f_kr_cmmt,2:copley_drive_sim,3:copley_drive_sim',
                   'DEVICE_SIMULATOR_AXIS_MODES': ','.join(f'{i}:linear' for i in range(4)),
                   'DEVICE_SIMULATOR_AXIS_PARAMETER_SETS': ','.join(f'{i}:temporary-{i}' for i in range(4)),
                   'DEVICE_SIMULATOR_MODEL_TIMEOUT_MS': '100'}
            processes = []
            master = pysoem.Master()
            try:
                with (root/'model.log').open('w') as model_log, (root/'slave.log').open('w') as slave_log:
                    model = subprocess.Popen([sys.executable, '-m', 'functional_model', '--environment',
                                              '--fixture-dir', str(root/'fixture'), '--socket', str(root/'model.sock')],
                                             env=env, stdout=model_log, stderr=model_log)
                    processes.append(model)
                    deadline = time.monotonic()+20
                    while not (root/'model.sock').exists():
                        check(model.poll() is None and time.monotonic()<deadline, 'model startup failed')
                        time.sleep(.02)
                    slave = subprocess.Popen(['/opt/simulator/bin/cmmt_simulator', 'fault-slave',
                                              str(root/'fixture/cmmt.json'), str(root/'fixture/contract.json'),
                                              str(root/'model.sock')], env=env, stdout=slave_log, stderr=slave_log)
                    processes.append(slave)
                    deadline = time.monotonic()+10
                    while 'CMMT_READY' not in (root/'slave.log').read_text():
                        check(slave.poll() is None and time.monotonic()<deadline, 'Slave startup failed')
                        time.sleep(.02)
                    master.open('fault-master')
                    check(master.config_init() == 4, 'four-axis discovery failed')
                    master.config_map()
                    check(master.state_check(pysoem.SAFEOP_STATE, 2_000_000) == pysoem.SAFEOP_STATE, 'SAFEOP failed')
                    cw = [6]*4
                    modes = [1]*4
                    def cycle(count=1):
                        wkc = 0
                        for _ in range(count):
                            for i, axis in enumerate(master.slaves):
                                axis.output = struct.pack('<HbiIihihB', cw[i], modes[i], 1000, 1000, 0, 0, 0, 0, 0)
                            master.send_processdata()
                            wkc = master.receive_processdata(5000)
                            time.sleep(.008)
                        return wkc
                    cycle(5)
                    master.state = pysoem.OP_STATE
                    master.write_state()
                    cycle(10)
                    check(master.state_check(pysoem.OP_STATE, 1_000_000) == pysoem.OP_STATE, 'OP failed')
                    for value in (6, 7, 15):
                        cw[:] = [value]*4
                        cycle(5)
                    sw = lambda i: int.from_bytes(master.slaves[i].input[:2], 'little')
                    check(all(sw(i)&0x6f == 0x27 for i in range(4)), 'initial Enable failed')
                    # Only Copley axis 2 rejects an unsupported cyclic mode.
                    modes[2] = 99
                    cycle(6)
                    check(sw(2)&8 and not sw(3)&8, 'axis Fault isolation failed')
                    modes[2] = 1
                    for value, count in ((15,2), (0x8f,2), (15,2), (6,5), (7,5)):
                        cw[2] = value
                        cycle(count)
                    check(sw(2)&0x6f == 0x23, 'Motion Server Reset sequence failed')
                    cw[2] = 15
                    cycle(5)
                    check(sw(2)&0x6f == 0x27, 're-Enable failed')
                    cw[2] = 0x3f
                    cycle(5)
                    check(sw(2)&0x1000, 'new PP setpoint not acknowledged')
                    cw[2] = 15
                    cycle(5)
                    check(not sw(2)&0x1000, 'PP ACK did not clear')
                    check(cycle() == master.expected_wkc, 'healthy WKC mismatch')
                    model.send_signal(signal.SIGSTOP if failure == 'timeout' else signal.SIGKILL)
                    good = 0
                    for _ in range(80):
                        check(cycle() == master.expected_wkc, 'WKC lost during Host failure')
                        good += 1
                    check(slave.poll() is None, 'Slave exited after Host failure')
                    check(all(sw(i)&8 and not sw(i)&4 for i in range(4)), 'Host Fault not projected to all axes')
                    check(int.from_bytes(master.slaves[2].sdo_read(0x6041, 0), 'little') & 8, 'Fault status SDO unavailable')
                    try:
                        master.slaves[2].sdo_read(0x6081, 0)
                    except pysoem.SdoError:
                        pass
                    else:
                        raise AssertionError('Unavailable model returned successful SDO')
                    # A late resumed Host must never clear the latched Fault.
                    if failure == 'timeout': model.send_signal(signal.SIGCONT)
                    cw[:] = [0x8f]*4
                    cycle(5)
                    check(all(sw(i)&8 for i in range(4)), 'Host Fault cleared by axis Reset')
                    print(json.dumps(dict(test=failure, axes=4, wkc=master.expected_wkc,
                                          successful_fault_cycles=good, result='passed')), flush=True)
            except Exception:
                for name in ('model.log', 'slave.log'):
                    if (root/name).exists(): print((root/name).read_text()[-12000:])
                raise
            finally:
                try: master.close()
                except Exception: pass
                for proc in reversed(processes):
                    if proc.poll() is None:
                        proc.send_signal(signal.SIGCONT)
                        proc.terminate()
                        try: proc.wait(timeout=3)
                        except subprocess.TimeoutExpired: proc.kill(); proc.wait()


if __name__ == '__main__': main()
