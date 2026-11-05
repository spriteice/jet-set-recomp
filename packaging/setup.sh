#!/bin/sh
# Set this folder up for your own disc, once: ./setup.sh "DISC_FOLDER/Jet Grind Radio (USA).cue"
# Writes disc.gdi and boot/1ST_READ.BIN here. Needs Python 3.
[ -n "$1" ] || { echo 'usage: ./setup.sh "DISC_FOLDER/Jet Grind Radio (USA).cue"' >&2; exit 2; }
# The .cue path is read before moving into this folder, so a relative one means what it did where the
# command was typed.
case "$1" in /*) cue="$1" ;; *) cue="$PWD/$1" ;; esac
cd "$(dirname "$0")" || exit 1
command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 isn't installed. Install your distribution's python3 package (SteamOS has it), then run setup again." >&2
    exit 1
}
python3 tools/02_make_gdi.py "$cue" disc.gdi || exit 1
python3 tools/03_get_boot_file.py disc.gdi boot/1ST_READ.BIN || exit 1
echo "Set up. Run ./play.sh."
