#!/usr/bin/env bash
# Make a delivery folder from a finished build, without the disc or the boot file.
#
#   scripts/20_package.sh linux|windows OUT_FOLDER
#
# A package holds translated code, so it goes to the maintainer's own devices only and is never published
# (docs/project-instructions.md, section 3). It reads the player's own disc at run time.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
platform="${1:-}"
out="${2:-}"
[ -n "$out" ] || { echo "usage: $0 linux|windows OUT_FOLDER" >&2; exit 2; }
dream="$root/third_party/dream-recomp"

mkdir -p "$out/licences" "$out/tools"
case "$platform" in
    linux)
        cp "$root/build/games/jgr/jgr_boot" "$out/"
        cp -P "${DREAM_LINUX_PREFIX:-$HOME/linux/prefix}"/lib/libSDL3.so* "$out/"
        cp "$root/packaging/play.sh" "$root/packaging/setup.sh" "$out/"
        ;;
    windows)
        cp "$root/build-win/games/jgr/jgr_boot.exe" "$out/"
        cp "${DREAM_WIN_PREFIX:-$HOME/win/prefix}/bin/SDL3.dll" "$out/"
        cp "$root/packaging/play.bat" "$root/packaging/setup.bat" "$out/"
        ;;
    *) echo "usage: $0 linux|windows OUT_FOLDER" >&2; exit 2 ;;
esac

cp "$root/games/jgr/jgr.toml" "$root/packaging/README.txt" "$out/"
cp "$root/data/inputs.sha256" "$out/tools/"
cp "$root/scripts/02_make_gdi.py" "$root/scripts/03_get_boot_file.py" "$out/tools/"
cp -r "$dream/tools/dcdisc/dcdisc" "$out/tools/dcdisc"
find "$out/tools" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$root/LICENSE" "$out/licences/LICENSE-JSR-recomp.txt"
cp "$dream/LICENSE" "$out/licences/LICENSE-dream-recomp.txt"
echo "packaged $platform in $out"
