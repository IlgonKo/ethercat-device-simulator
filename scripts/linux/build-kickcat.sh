#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/third_party/KickCAT"
BUILD="$ROOT/build/kickcat"
VENV="$ROOT/.venv-kickcat"
for tool in git python3 cmake gcc g++ make; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool (see Doc/RF/RF-001-linux-kickcat.md)" >&2; exit 1; }
done
test -f "$SRC/scripts/setup_build.sh" || { echo "Run: git submodule update --init --recursive" >&2; exit 1; }
if [[ ! -x "$VENV/bin/conan" ]]; then
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install 'conan==2.10.2'
fi
export PATH="$VENV/bin:$PATH"
bash "$SRC/scripts/configure.sh" "$BUILD" -ni --without=all --with=simulation --with=esi_parser --with=master_examples
bash "$SRC/scripts/setup_build.sh" "$BUILD"
cmake --build "$BUILD" --target network_simulator simulated_bus --parallel "${BUILD_JOBS:-2}"
git -C "$SRC" rev-parse HEAD > "$BUILD/kickcat-revision.txt"
echo "Built: $BUILD/simulation/network_simulator"
echo "After each rebuild, run the setcap command in Doc/RF/RF-001-linux-kickcat.md."
