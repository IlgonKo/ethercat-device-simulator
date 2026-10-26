#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 0 ]] || { echo "Usage: bash scripts/docker/logs.sh"; [[ "${1:-}" == --help ]] && exit 0; exit 2; }
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
"${COMPOSE[@]}" logs -f --tail=100 simulator
