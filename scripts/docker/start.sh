#!/usr/bin/env bash
set -euo pipefail
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --build ) ]]; then
    echo "Usage: bash scripts/docker/start.sh [--build]"
    [[ "${1:-}" == --help ]] && exit 0
    exit 2
fi
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
if [[ "${1:-}" == --build ]]; then
    "${COMPOSE[@]}" build simulator
fi
echo "Starting Simulator using ${PROJECT_ROOT}/.env"
if ! "${COMPOSE[@]}" up -d --no-build --force-recreate --wait --wait-timeout 30 simulator; then
    "${COMPOSE[@]}" logs --tail=50 simulator >&2 || true
    exit 1
fi
echo "Simulator started. Health indicates process readiness, not EtherCAT OP/WKC."
echo "Logs: bash scripts/docker/logs.sh"
