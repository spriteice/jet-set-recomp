#!/bin/sh
# Copy your disc into this folder, once, so the folder is complete and can move or be added to Steam:
#   ./copy-disc.sh "USB_STICK/Jet Grind Radio (USA)/Jet Grind Radio (USA).cue"
# Copies the .cue and its tracks (1.2 GB) into disc/, checks them against the hash list, then writes
# disc.gdi and boot/1ST_READ.BIN here, with paths inside this folder. Needs Python 3. Afterwards the
# copy you named isn't needed. To read the disc where it is instead, run setup.sh.
cd "$(dirname "$0")" || exit 1
[ -n "$1" ] || { echo 'usage: ./copy-disc.sh "DISC_FOLDER/Jet Grind Radio (USA).cue"' >&2; exit 2; }
cue="$1"
[ -f "$cue" ] || { echo "No .cue at $cue. Name your disc's .cue file, with its folder." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 isn't installed. Install your distribution's python3 package (SteamOS has it), then run this again." >&2
    exit 1
}
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum isn't installed: it comes with coreutils." >&2; exit 1; }
from="$(dirname "$cue")"
# The .cue names its track files: FILE "name" BINARY.
tracks="$(sed -n 's/^[[:space:]]*FILE "\(.*\)" BINARY[[:space:]]*$/\1/p' "$cue")"
[ -n "$tracks" ] || { echo "$cue names no track files: it isn't a disc .cue this can read." >&2; exit 1; }
mkdir -p disc || exit 1

copy() {  # copy NAME: from the disc's folder into disc/
    [ -f "$from/$1" ] || {
        echo "The .cue names a track that isn't beside it: $1. Keep the .cue and its .bin files together, as they were dumped." >&2
        exit 1
    }
    echo "copying $1"
    cp "$from/$1" "disc/$1" || { echo "Couldn't copy $1 into disc/. Is there 1.2 GB free here?" >&2; exit 1; }
}
copy "$(basename "$cue")"
# The loop runs in a subshell, so a failed copy ends the loop with its status, and then the script.
printf '%s\n' "$tracks" | while IFS= read -r name; do copy "$name"; done || exit 1

# Every copy against the hash list, by name and content. Comments and the boot file (not made yet) are
# left out of the list. A disc that doesn't match is a different release, and the game needs this one.
if ! grep -v '^#' tools/inputs.sha256 | grep -v ' 1ST_READ\.BIN$' | (cd disc && sha256sum -c --quiet -); then
    echo "The copied files don't match tools/inputs.sha256 (the lines above say which). The game needs Jet Grind Radio (USA), MK-51058 V1.005, with its files named as dumped. The copies in disc/ were removed, and nothing was set up." >&2
    rm -f "disc/$(basename "$cue")"
    printf '%s\n' "$tracks" | while IFS= read -r name; do rm -f "disc/$name"; done
    exit 1
fi
python3 tools/02_make_gdi.py "disc/$(basename "$cue")" disc.gdi || exit 1
python3 tools/03_get_boot_file.py disc.gdi boot/1ST_READ.BIN || exit 1
echo "Set up: your disc is in disc/, and the copy in $from isn't needed any more. Run ./play.sh."
