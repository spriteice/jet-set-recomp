#!/usr/bin/env bash
# Build jgr_boot for Linux, in build/. Needs games/jgr/boot/1ST_READ.BIN and games/jgr/disc.gdi, and
# takes about 15 minutes: translating re-emits 81 MB of C++ in one unit.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
linux_prefix="${DREAM_LINUX_PREFIX:-$HOME/linux/prefix}"
"$root/scripts/01_fetch_dream_recomp.sh"

cmake -S "$root" -B "$root/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_PREFIX_PATH="$linux_prefix" -DDREAM_DEV_INTERPRETER=ON
cmake --build "$root/build" --target jgr_boot
echo "built $root/build/games/jgr/jgr_boot"
