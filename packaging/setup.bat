@echo off
rem Set this folder up for your own disc, once: setup.bat "DISC_FOLDER\Jet Grind Radio (USA).cue"
rem Writes disc.gdi and boot\1ST_READ.BIN here. Needs Python 3.
cd /d "%~dp0"
if "%~1"=="" (
    echo usage: setup.bat "DISC_FOLDER\Jet Grind Radio ^(USA^).cue"
    pause
    exit /b 2
)
python tools\02_make_gdi.py "%~1" disc.gdi || goto :failed
python tools\03_get_boot_file.py disc.gdi boot\1ST_READ.BIN || goto :failed
echo Set up. Run play.bat.
exit /b 0

:failed
echo Setup failed: see the message above.
pause
exit /b 1
