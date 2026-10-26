#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 0 ]] || { echo "Usage: bash scripts/docker/validate.sh"; [[ "${1:-}" == --help ]] && exit 0; exit 2; }
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
if [[ -n "$("${COMPOSE[@]}" ps --status running -q simulator)" ]]; then
    echo "Stop Simulator before validating the same parameter store." >&2
    exit 1
fi
"${COMPOSE[@]}" run --rm --no-deps simulator --validate-only
