@echo off
cd /d "%~dp0"
rem Each run keeps its own log in logs\, named by its start time. None is overwritten.
if not exist logs mkdir logs
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "JGR_RUN=%%t"
jgr_boot.exe --config jgr.toml --window --vmu vmu-a1.bin --report "logs\run-%JGR_RUN%.txt" %*
