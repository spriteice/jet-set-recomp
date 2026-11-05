#!/bin/sh
cd "$(dirname "$0")" || exit 1
mkdir -p logs

# Say what went wrong where it can be seen. Steam's Game Mode shows no terminal, so the message also
# goes to logs/launcher.txt, and to a dialog when the desktop has a tool for one (JGR_NO_DIALOG=1
# turns that off, as the tests do).
fail() {
    echo "$1" >&2
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> logs/launcher.txt
    if [ -n "${JGR_NO_DIALOG:-}" ]; then
        :
    elif command -v zenity >/dev/null 2>&1; then
        zenity --error --title "Jet Grind Radio" --text "$1" >/dev/null 2>&1
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Jet Grind Radio" --error "$1" >/dev/null 2>&1
    fi
}

# The game can't start without the files setup makes from your disc, so say so instead of failing silently.
for need in disc.gdi boot/1ST_READ.BIN; do
    if [ ! -f "$need" ]; then
        fail "Missing $need. Run setup first (on SteamOS, in Desktop Mode): ./copy-disc.sh \"STICK/Jet Grind Radio (USA).cue\" copies your disc into this folder, or ./setup.sh \"DISC_FOLDER/Jet Grind Radio (USA).cue\" reads it where it is."
        exit 1
    fi
done
# Each run keeps its own log in logs/, named by its start time. None is overwritten.
log="logs/run-$(date +%Y-%m-%d_%H-%M-%S).txt"
LD_LIBRARY_PATH=".${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./jgr_boot --config jgr.toml --window --vmu vmu-a1.bin --report "$log" "$@"
status=$?
[ "$status" -eq 0 ] || fail "jgr_boot exited with code $status. Send back $log if it exists, and logs/launcher.txt."
exit "$status"
