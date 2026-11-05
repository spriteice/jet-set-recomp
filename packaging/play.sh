#!/bin/sh
cd "$(dirname "$0")" || exit 1
# The game can't start without the files setup makes from your disc, so say so instead of failing silently.
for need in disc.gdi boot/1ST_READ.BIN; do
    if [ ! -f "$need" ]; then
        echo "Missing $need. Run setup first: ./setup.sh \"DISC_FOLDER/Jet Grind Radio (USA).cue\"" >&2
        exit 1
    fi
done
# Each run keeps its own log in logs/, named by its start time. None is overwritten.
mkdir -p logs
log="logs/run-$(date +%Y-%m-%d_%H-%M-%S).txt"
LD_LIBRARY_PATH=".${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./jgr_boot --config jgr.toml --window --vmu vmu-a1.bin --report "$log" "$@"
status=$?
[ "$status" -eq 0 ] || echo "jgr_boot exited with code $status. Send back $log if it exists." >&2
exit "$status"
