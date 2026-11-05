#!/bin/sh
# Set this folder up for your own disc, once: ./setup.sh "DISC_FOLDER/Jet Grind Radio (USA).cue"
# Writes disc.gdi and boot/1ST_READ.BIN here. Needs Python 3.
cd "$(dirname "$0")" || exit 1
[ -n "$1" ] || { echo 'usage: ./setup.sh "DISC_FOLDER/Jet Grind Radio (USA).cue"' >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 isn't installed. Install your distribution's python3 package (SteamOS has it), then run setup again." >&2
    exit 1
}
python3 tools/02_make_gdi.py "$1" disc.gdi || exit 1
python3 tools/03_get_boot_file.py disc.gdi boot/1ST_READ.BIN || exit 1
echo "Set up. Run ./play.sh."
