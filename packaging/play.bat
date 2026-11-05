@echo off
cd /d "%~dp0"
jgr_boot.exe --config jgr.toml --window --vmu vmu-a1.bin --report last-run.txt %*
