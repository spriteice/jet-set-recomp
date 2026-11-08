#!/usr/bin/env bash
# Cross-build jgr_boot.exe for Windows from Linux, in build-win/: clang for MinGW-w64, always with
# -mfma, which the toolchain file sets (MinGW's own fmaf isn't fused). Runs in a cloud sandbox.
# Needs games/jgr/boot/1ST_READ.BIN and scripts/09_setup_sandbox.sh's Windows prefix.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Without the boot file there's no jgr_boot target, and the build would fail late with "unknown target".
boot="$root/games/jgr/boot/1ST_READ.BIN"
if [ ! -f "$boot" ]; then
    echo "No $boot: make it first (docs/build-and-test-reference.md, Building, steps 1 to 3)." >&2
    exit 1
fi
export DREAM_WIN_PREFIX="${DREAM_WIN_PREFIX:-$HOME/win/prefix}"
"$root/scripts/01_fetch_dream_recomp.sh"
dream="$root/third_party/dream-recomp"

# The translator has to run on the build machine, so it's built for Linux first.
cmake -S "$dream" -B "$root/build-host" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DDREAM_RENDERER=OFF -DDREAM_BUILD_TESTS=OFF
cmake --build "$root/build-host" --target dream-translate
translate="$(find "$root/build-host" -type f -name dream-translate -perm -u+x | head -n 1)"
[ -n "$translate" ] || { echo "no dream-translate in build-host" >&2; exit 1; }

cmake -S "$root" -B "$root/build-win" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$dream/cmake/toolchains/mingw-w64-clang.cmake" \
    -DDREAM_HOST_TRANSLATE="$translate" -DDREAM_DEV_INTERPRETER=ON -DDREAM_BUILD_TESTS=OFF \
    -DVulkan_INCLUDE_DIR="$DREAM_WIN_PREFIX/include" -DVulkan_LIBRARY="$DREAM_WIN_PREFIX/lib/libvulkan-1.a" \
    -DSDL3_DIR="$DREAM_WIN_PREFIX/lib/cmake/SDL3"
cmake --build "$root/build-win" --target jgr_boot
echo "built $root/build-win/games/jgr/jgr_boot.exe"
