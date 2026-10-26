#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 0 ]] || { echo "Usage: bash scripts/docker/stop.sh"; [[ "${1:-}" == --help ]] && exit 0; exit 2; }
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
"${COMPOSE[@]}" stop simulator
"${COMPOSE[@]}" rm -f simulator
echo "Simulator stopped. Parameter files in STATE_DIR are preserved."
