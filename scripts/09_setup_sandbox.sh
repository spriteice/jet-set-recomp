#!/usr/bin/env bash
# Install what the builds and checks need, in a cloud sandbox only. Never run this on the maintainer's PC
# (docs/project-instructions.md, section 4 lists what may be installed).
#
# Makes the Windows prefix too: SDL3 cross-built from source, and the Vulkan import library.
set -euo pipefail

SDL_VERSION=3.2.24
prefix="${DREAM_WIN_PREFIX:-$HOME/win/prefix}"
linux_prefix="${DREAM_LINUX_PREFIX:-$HOME/linux/prefix}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sudo_cmd=""; [ "$(id -u)" -eq 0 ] || sudo_cmd=sudo

$sudo_cmd apt-get update -qq
$sudo_cmd apt-get install -y -qq clang lld cmake ninja-build pipx python3 mingw-w64 \
    libvulkan-dev glslc shellcheck libx11-dev libxext-dev libwayland-dev libxkbcommon-dev \
    libasound2-dev libpulse-dev libpipewire-0.3-dev
pipx install "clang-format==20.1.7"

work="$(mktemp -d)"
git clone -q --depth 1 --branch "release-$SDL_VERSION" https://github.com/libsdl-org/SDL "$work/SDL"

cmake -S "$work/SDL" -B "$work/sdl-linux" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$linux_prefix" -DSDL_TESTS=OFF
cmake --build "$work/sdl-linux" --target install
# SDL3 opens ALSA, PulseAudio and PipeWire at run time, so without their headers (the three packages
# above) it builds with no sound system and the game is silent (known bug 21). Checked here, where the
# cause is, not on the device.
python3 "$root/scripts/21_check_sdl_audio.py" "$(readlink -f "$linux_prefix/lib/libSDL3.so.0")"

mkdir -p "$prefix/lib"
export DREAM_WIN_PREFIX="$prefix"
"$root/scripts/01_fetch_dream_recomp.sh"
toolchain="$root/third_party/dream-recomp/cmake/toolchains/mingw-w64-clang.cmake"
cmake -S "$work/SDL" -B "$work/sdl-win" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$toolchain" -DCMAKE_INSTALL_PREFIX="$prefix" -DSDL_TESTS=OFF
cmake --build "$work/sdl-win" --target install
python3 "$root/scripts/21_check_sdl_audio.py" "$prefix/bin/SDL3.dll"
x86_64-w64-mingw32-dlltool \
    -d "$root/third_party/dream-recomp/cmake/toolchains/vulkan-1.def" -l "$prefix/lib/libvulkan-1.a"
# The Vulkan headers go in the prefix too: naming /usr/include in a cross build puts glibc's headers
# ahead of MinGW's.
mkdir -p "$prefix/include"
cp -r /usr/include/vulkan /usr/include/vk_video "$prefix/include/"

rm -rf "$work"
echo "sandbox ready: Windows prefix $prefix, Linux prefix $linux_prefix"
