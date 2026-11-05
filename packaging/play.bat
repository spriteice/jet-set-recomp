@echo off
cd /d "%~dp0"
rem The game cannot start without the files setup makes from your disc, so say so instead of failing silently.
if not exist disc.gdi goto :nosetup
if not exist boot\1ST_READ.BIN goto :nosetup
rem Each run keeps its own log in logs\, named by its start time. None is overwritten.
if not exist logs mkdir logs
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "JGR_RUN=%%t"
jgr_boot.exe --config jgr.toml --window --vmu vmu-a1.bin --report "logs\run-%JGR_RUN%.txt" %*
if not "%errorlevel%"=="0" (
    echo jgr_boot exited with code %errorlevel%. Send back logs\run-%JGR_RUN%.txt if it exists.
    pause
    exit /b %errorlevel%
)
exit /b 0

:nosetup
echo Missing disc.gdi or boot\1ST_READ.BIN. Run setup first: setup.bat "DISC_FOLDER\Jet Grind Radio (USA).cue"
pause
exit /b 1
