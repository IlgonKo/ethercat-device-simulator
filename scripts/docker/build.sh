#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 0 ]] || { echo "Usage: bash scripts/docker/build.sh"; [[ "${1:-}" == --help ]] && exit 0; exit 2; }
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
"${COMPOSE[@]}" build simulator
