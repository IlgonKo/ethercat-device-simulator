#!/usr/bin/env bash
# Shared setup; never source .env as shell code (axis lists contain spaces).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
if [[ "$(uname -s)" != Linux ]]; then
    echo "Run these scripts on the Linux Edge PC." >&2
    exit 1
fi
command -v docker >/dev/null || { echo "Docker is not installed." >&2; exit 1; }
[[ -f "${PROJECT_ROOT}/.env" ]] || {
    echo "Missing ${PROJECT_ROOT}/.env. Copy .env.example and configure it first." >&2
    exit 1
}
cd "${PROJECT_ROOT}"
command -v python3 >/dev/null || { echo "Python 3 is required to normalize .env." >&2; exit 1; }
DEVICE_SIMULATOR_ENV_FILE="$(python3 "${SCRIPT_DIR}/prepare-env.py")"
export DEVICE_SIMULATOR_ENV_FILE
COMPOSE=(docker compose --project-directory "${PROJECT_ROOT}" -f "${PROJECT_ROOT}/compose.yaml" --env-file "${DEVICE_SIMULATOR_ENV_FILE}")
"${COMPOSE[@]}" config --quiet
