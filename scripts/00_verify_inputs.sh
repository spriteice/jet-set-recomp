#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Check the disc against data/inputs.sha256. Every run starts here (docs/project-instructions.md,
# section 3). A disc that doesn't match is a different release: stop, and tell the maintainer.
#
#   scripts/00_verify_inputs.sh "/path/to/Jet Grind Radio (USA)" [path/to/1ST_READ.BIN]
#
# The disc folder may also come from JGR_DISC_DIR. The boot file defaults to
# games/jgr/boot/1ST_READ.BIN, and is checked only once it exists (scripts/03_get_boot_file.py makes it).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
disc_dir="${1:-${JGR_DISC_DIR:-}}"
boot_file="${2:-$root/games/jgr/boot/1ST_READ.BIN}"
list="$root/data/inputs.sha256"

if [ -z "$disc_dir" ] || [ ! -d "$disc_dir" ]; then
    echo "usage: $0 DISC_FOLDER [BOOT_FILE] (no such folder: '${disc_dir}')" >&2
    exit 2
fi

failed=0
check() {  # check FILE EXPECTED NAME
    local actual
    if [ ! -f "$1" ]; then
        echo "MISSING   $3"
        failed=1
        return
    fi
    actual="$(sha256sum "$1" | cut -d' ' -f1)"
    if [ "$actual" = "$2" ]; then
        echo "ok        $3"
    else
        echo "MISMATCH  $3: $actual, expected $2"
        failed=1
    fi
}

while read -r expected name; do
    case "$expected" in ''|\#*) continue ;; esac
    if [ "$name" = "1ST_READ.BIN" ]; then
        if [ -f "$boot_file" ]; then
            check "$boot_file" "$expected" "$name"
        else
            echo "not yet   $name (scripts/03_get_boot_file.py makes it)"
        fi
    else
        check "$disc_dir/$name" "$expected" "$name"
    fi
done < "$list"

if [ "$failed" -ne 0 ]; then
    echo "The disc does not match data/inputs.sha256: this is a different release. Stop, and tell the maintainer." >&2
    exit 1
fi
echo "inputs verified: Jet Grind Radio (USA), MK-51058 V1.005"
