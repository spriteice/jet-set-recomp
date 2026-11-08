@echo off
rem SPDX-License-Identifier: GPL-2.0-only
rem Set this folder up for your own disc, once: setup.bat "DISC_FOLDER\Jet Grind Radio (USA).cue"
rem Writes disc.gdi and boot\1ST_READ.BIN here. Needs Python 3 from python.org.
if "%~1"=="" (
    echo usage: setup.bat "DISC_FOLDER\Jet Grind Radio ^(USA^).cue"
    pause
    exit /b 2
)
rem The .cue path is made a full path before moving into this folder, so a relative one means what it
rem did where the command was typed.
set "cue=%~f1"
cd /d "%~dp0"
rem Without Python, Windows 11 answers "python" with its Store alias, which prints Microsoft's message
rem and fails. Check first, and say what to install.
python --version >nul 2>nul || goto :nopython
python tools\02_make_gdi.py "%cue%" disc.gdi || goto :failed
python tools\03_get_boot_file.py disc.gdi boot\1ST_READ.BIN || goto :failed
echo Set up. Run play.bat.
exit /b 0

:failed
echo Setup failed: see the message above.
pause
exit /b 1

:nopython
echo Python 3 isn't installed. Install it from https://www.python.org/downloads/ with "Add python.exe to PATH" ticked, then run setup again.
pause
exit /b 1
