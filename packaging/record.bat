@echo off
cd /d "%~dp0"
rem Records a play-through for the regression gate: a copy of your save as the memory card (so the
rem replay can start from the same save, and your save isn't written), a fixed console clock, and the
rem controller state of every frame where it changes. The files it writes hold inputs, counts and
rem addresses only, nothing from the disc.
if not exist disc.gdi goto :nosetup
if not exist boot\1ST_READ.BIN goto :nosetup
if not exist vmu-a1.bin goto :nosave
if not exist logs mkdir logs
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set "JGR_RUN=%%t"
rem Two copies: the run plays on -card.bin, which it saves to, and -card-start.bin is kept as it was, the
rem card a replay of this recording has to start from, even after vmu-a1.bin has been played on again.
copy /b vmu-a1.bin "logs\record-%JGR_RUN%-card-start.bin" >nul || (echo Could not copy vmu-a1.bin to logs\. & pause & exit /b 1)
copy /b vmu-a1.bin "logs\record-%JGR_RUN%-card.bin" >nul || (echo Could not copy vmu-a1.bin to logs\. & pause & exit /b 1)
rem By full path: an account with NoDefaultCurrentDirectoryInExePath set doesn't look in this folder.
"%~dp0jgr_boot.exe" --config jgr.toml --window --rtc-seed 1 --vmu "logs\record-%JGR_RUN%-card.bin" --record-input "logs\record-%JGR_RUN%-input.txt" --report "logs\record-%JGR_RUN%-report.txt" %*
if not "%errorlevel%"=="0" (
    echo jgr_boot exited with code %errorlevel%. Send back logs\record-%JGR_RUN%-report.txt if it exists.
    pause
    exit /b %errorlevel%
)
echo Recorded: logs\record-%JGR_RUN%-input.txt and logs\record-%JGR_RUN%-report.txt. Send those two back.
echo The card it started from, logs\record-%JGR_RUN%-card-start.bin, stays on this PC like your save.
pause
exit /b 0

:nosetup
echo Missing disc.gdi or boot\1ST_READ.BIN. Run setup first: setup.bat "DISC_FOLDER\Jet Grind Radio (USA).cue"
pause
exit /b 1

:nosave
echo Missing vmu-a1.bin, the save this recording starts from.
pause
exit /b 1
