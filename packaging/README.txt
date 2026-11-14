Jet Grind Radio (Dreamcast) on dream-recomp: test build
=======================================================

The Dreamcast version's boot program, translated ahead of time to native x86-64 code by
dream-recomp (github.com/phobos665/dream-recomp, GPL-2.0, by phobos665), with its Vulkan renderer
and SDL3 window and sound. This folder holds no game files: it reads your own disc. SEGA owns Jet
Grind Radio; bring your own disc.

Setting up, once, with Python 3 and your own Jet Grind Radio (USA), MK-51058 V1.005
-----------------------------------------------------------------------------------
Setup needs Python 3. Windows doesn't come with it: install it from python.org with "Add python.exe
to PATH" ticked. SteamOS and most Linux desktops already have it. Then run setup once, naming your
disc's .cue:

  setup.bat "DISC_FOLDER\Jet Grind Radio (USA).cue"        (Windows)
  ./setup.sh "DISC_FOLDER/Jet Grind Radio (USA).cue"        (Linux)

It writes disc.gdi and boot/1ST_READ.BIN here, and checks the boot file against the hash list. If the
disc moves, run it again.

Copying the disc into this folder (Linux)
-----------------------------------------
When the disc arrives on a USB stick, as on a handheld, run copy-disc.sh once instead of setup.sh:

  ./copy-disc.sh "USB_STICK/Jet Grind Radio (USA)/Jet Grind Radio (USA).cue"

It copies the .cue and the tracks (1.2 GB) into disc/, checks every copy against the hash list, and
sets up with paths inside this folder. The folder is then complete: it can move, and the stick can
go. (Setup writes paths inside the folder too whenever the disc is already under it.)

Playing
-------
Run play.bat on Windows or play.sh on Linux. Until setup has run, they say what's missing and
stop. On a Steam Deck or another SteamOS device, run copy-disc.sh (or setup.sh) once in Desktop
Mode, then add play.sh to Steam as a non-Steam game, and always start it from Steam, in Game Mode
or in Desktop Mode. SteamOS gives the built-in controller to a game only when Steam starts it:
started from a terminal such as Konsole, the game runs but the controller does nothing, as with
other ports and emulators. If the game can't start, the reason is in logs/launcher.txt, and
anything the game itself printed is in logs/stderr-<start time>.txt. A controller is best: the game
steers with the stick.

Keyboard: arrow keys are the d-pad, Z X A S are A B X Y, Return is Start, Q and W are the triggers.
F1 opens the binding screen (a pad's select button does too), F10 shows the frame-rate counter, F12
writes a screenshot, Esc quits. The memory card vmu-a1.bin is made, blank and formatted, on the
first run. Each run writes its own log when the game closes, in logs/, named by the time the run
started (logs/run-2026-11-05_09-45-16.txt, say), so no run's log is overwritten. A log holds counts
only (frames, traps, unmapped memory accesses, calls the translator missed). Send back the logs from
a test.

Recording a play-through (Windows)
----------------------------------
record.bat plays like play.bat, with two differences: it plays on a copy of your save, so
vmu-a1.bin isn't written, and it records the controls, frame by frame, to
logs\record-<start time>-input.txt with a fixed console clock, so the run can be replayed exactly.
It keeps an untouched copy of the card it started from, logs\record-<start time>-card-start.bin,
which a replay starts from. The input file and the report hold controls and counts only: send
those two back. The cards stay on your PC.

What is known
-------------
- Needs Vulkan and a CPU with FMA3 (Intel since 2013, AMD since 2012).
- Shadows are missing: the renderer decodes the Dreamcast's modifier volumes but doesn't draw them
  yet, and Jet Grind Radio uses them in every 3D scene.
- Code the translator never found runs interpreted, more slowly, instead of the game stopping, and
  the run's log lists it.
