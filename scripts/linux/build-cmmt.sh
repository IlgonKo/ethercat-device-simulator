#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
test -f "$ROOT/build/kickcat/toolchain.cmake" || { echo 'Run build-kickcat.sh first' >&2; exit 1; }
cmake -S "$ROOT" -B "$ROOT/build/timing" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE="$ROOT/build/kickcat/toolchain.cmake" \
  -DCMAKE_PREFIX_PATH="$ROOT/build/kickcat"
cmake --build "$ROOT/build/timing" --target cmmt_simulator --parallel 2
echo "Built build/timing/cmmt_simulator. Package with: bash scripts/docker/build.sh"
