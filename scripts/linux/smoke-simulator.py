#!/usr/bin/env python3
"""Verify the simulator binds the dedicated raw interface and stops cleanly."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[2]
nic = sys.argv[1] if len(sys.argv) == 2 else "enp1s0"
if len(sys.argv) > 2:
    raise SystemExit("Usage: smoke-simulator.py [dedicated-interface]")
ifindex = (Path("/sys/class/net") / nic / "ifindex").read_text().strip()
def ethercat_sockets():
    rows = Path("/proc/net/packet").read_text().splitlines()[1:]
    return {f[-1] for row in rows if len(f := row.split()) >= 9
            and f[3].lower() == "88a4" and f[4] == ifindex}

before = ethercat_sockets()
with tempfile.TemporaryFile(mode="w+t") as log:
    process = subprocess.Popen(
        ["bash", str(root / "scripts/linux/run-simulator.sh"), nic],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        bound = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and process.poll() is None:
            bound = bool(ethercat_sockets() - before)
            if bound:
                time.sleep(1)
                if process.poll() is not None:
                    raise RuntimeError("Simulator exited after opening the socket")
                break
            time.sleep(0.1)
        if not bound:
            raise RuntimeError("No EtherCAT socket bound by simulator to " + nic)
        os.killpg(process.pid, signal.SIGTERM)
        result = process.wait(timeout=5)
        if result != 0:
            raise RuntimeError(f"Simulator exit code: {result}")
        if ethercat_sockets() - before:
            raise RuntimeError("EtherCAT socket remains after simulator shutdown")
        print(f"PASS: EtherCAT socket bound to {nic}; SIGTERM exit code 0.")
        print("Physical master traffic and PySOEM interoperability remain stage 2.")
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        log.seek(0)
        print(log.read(), end="")
