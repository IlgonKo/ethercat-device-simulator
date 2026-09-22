#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NIC="${1:-enp1s0}"
BIN="$ROOT/build/kickcat/simulation/network_simulator"
CONFIG="${KICKCAT_SLAVE_CONFIG:-$ROOT/configs/kickcat/basic-slave.json}"
[[ $# -le 1 ]] || { echo "Usage: $0 [dedicated-interface]" >&2; exit 2; }
test -x "$BIN" || { echo "Build first: bash scripts/linux/build-kickcat.sh" >&2; exit 1; }
test -d "/sys/class/net/$NIC" || { echo "Interface not found: $NIC" >&2; exit 1; }
# IP addresses do not prevent raw EtherCAT access. Protect only the current SSH interface.
python3 - "$NIC" <<'PY'
import ipaddress
import json
import os
import subprocess
import sys
nic = sys.argv[1]
interfaces = json.loads(subprocess.check_output(["ip", "-j", "addr", "show", "dev", nic]))
ssh = os.environ.get("SSH_CONNECTION", "").split()
ssh_local = ipaddress.ip_address(ssh[2].split("%")[0]) if len(ssh) == 4 else None
for interface in interfaces:
    for entry in interface.get("addr_info", []):
        address = ipaddress.ip_address(entry["local"].split("%")[0])
        if address == ssh_local:
            sys.exit(f"Refusing current SSH interface: {nic}")
PY
[[ "$(cat "/sys/class/net/$NIC/carrier")" == 1 ]] || { echo "No carrier on $NIC; check cable/link." >&2; exit 1; }
if [[ $EUID -ne 0 ]]; then
    CAPS="$(getcap "$BIN")"
    if [[ "$CAPS" != *cap_net_raw* || "$CAPS" != *cap_net_admin* || "$CAPS" != *+ep* && "$CAPS" != *=ep* ]]; then
        echo "Missing capabilities. Run:" >&2
        printf "sudo setcap cap_net_raw,cap_net_admin=ep '%s'\n" "$BIN" >&2
        exit 1
    fi
fi
echo "Starting basic Slave on $NIC; Ctrl+C stops it."
exec "$BIN" -i "$NIC" -s "$CONFIG"
