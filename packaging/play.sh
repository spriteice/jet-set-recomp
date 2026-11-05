#!/bin/sh
cd "$(dirname "$0")" || exit 1
# Each run keeps its own log in logs/, named by its start time. None is overwritten.
mkdir -p logs
log="logs/run-$(date +%Y-%m-%d_%H-%M-%S).txt"
LD_LIBRARY_PATH=".${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" exec ./jgr_boot --config jgr.toml --window --vmu vmu-a1.bin --report "$log" "$@"
