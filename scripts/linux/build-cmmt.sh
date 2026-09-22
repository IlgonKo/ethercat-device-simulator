#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
test -f "$ROOT/build/kickcat/toolchain.cmake" || { echo 'Run build-kickcat.sh first' >&2; exit 1; }
cmake -S "$ROOT" -B "$ROOT/build/cmmt" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE="$ROOT/build/kickcat/toolchain.cmake" \
  -DCMAKE_PREFIX_PATH="$ROOT/build/kickcat"
cmake --build "$ROOT/build/cmmt" --target cmmt_simulator --parallel 2
echo "Set capabilities after building: sudo setcap cap_net_raw,cap_net_admin=ep $ROOT/build/cmmt/cmmt_simulator"
