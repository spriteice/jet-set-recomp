#!/bin/sh
cd "$(dirname "$0")" || exit 1
LD_LIBRARY_PATH=".${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" exec ./jgr_boot --config jgr.toml --window --vmu vmu-a1.bin --report last-run.txt "$@"
