#!/usr/bin/env bash
# Fetch dream-recomp into third_party/dream-recomp at the commit in data/dream-recomp.pin. It's
# fetched, never vendored: third_party/ is ignored, and nothing in it is committed here.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
url="${DREAM_RECOMP_URL:-https://github.com/spriteice/dream-recomp}"
dest="$root/third_party/dream-recomp"
pin="$(grep -v '^#' "$root/data/dream-recomp.pin" | head -n 1 | tr -d '[:space:]')"

case "$pin" in
    *[!0-9a-f]*|'') echo "data/dream-recomp.pin holds no hash" >&2; exit 2 ;;
esac
if [ "${#pin}" -ne 40 ]; then
    echo "data/dream-recomp.pin must hold a full 40-digit hash, not '$pin'" >&2
    exit 2
fi

if [ ! -e "$dest/.git" ]; then
    mkdir -p "$dest"
    git -C "$dest" init -q
    git -C "$dest" remote add origin "$url"
fi

if [ -n "$(git -C "$dest" status --porcelain)" ]; then
    echo "$dest has local changes. Translator and runtime fixes go on spriteice/dream-recomp's main." >&2
    exit 1
fi

if ! git -C "$dest" cat-file -e "$pin^{commit}" 2>/dev/null; then
    git -C "$dest" fetch -q --depth 1 origin "$pin"
fi
git -C "$dest" checkout -q --detach "$pin"
git -C "$dest" submodule update -q --init --recursive

actual="$(git -C "$dest" rev-parse HEAD)"
if [ "$actual" != "$pin" ]; then
    echo "third_party/dream-recomp is at $actual, not the pinned $pin" >&2
    exit 1
fi
echo "dream-recomp at $pin"
