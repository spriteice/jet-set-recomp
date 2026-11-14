# Build and test reference

How builds of Jet Set Recomp are made, checked, delivered and reported. It's written by the maintainer
("I"), who never builds by hand and only runs what's delivered, for whoever makes them ("you").

## Test devices

- **Windows:** desktop PC, Windows 11, i7-10700K, 32 GB, RTX 2080 Ti.
- **Linux:** ROG Xbox Ally X on SteamOS. Builds must work in Desktop Mode and Game Mode (gamescope).

## Where the work runs

- **The cloud,** a thread's sandbox: code, checks, Linux builds, Windows cross-builds, and every commit
  and push. The tools section 4 of the instructions lists may be installed there
  (`scripts/09_setup_sandbox.sh`). Every clone is set up first with `scripts/08_git_setup.sh`.
  Packages come from the usual archives. Ubuntu's snapshot server is never used by a build: if pinned
  packages are ever needed, they're pushed to our GitHub first, and every local build, sandbox and
  GitHub CI run installs them from there. The server is used only to update that copy, when a package
  needs it (section 4 of the instructions). The audit flags the server in any script, workflow or
  config here, so the copy's own update script lives with the copy.
- **My PC,** through folder access for files (reading, copying, writing the claim) and Remote Control
  for running anything, and only for what needs the PC itself, such as running a Windows build or
  copying the disc. Everything is under `E:\Games\Ports\jsr\DC`: the disc in `Game Files\Dreamcast\`, builds in
  `Building\`. Before a Remote Control session, a build or a test run there, claim the PC in
  `E:\Games\Ports\jsrf\Claude\building-on-pc\PC-IN-USE.md`, and clear the claim when the session
  ends, as section 4 of the instructions says. The claim's "what you'll run" says whether a game
  window opens. Nothing is installed, committed or pushed from there. The `jsrf-build` WSL
  distribution there belongs to another project: don't use it.

A session on the PC uses Git for Windows by full path (`C:\Program Files\Git\cmd\git.exe`), because
devkitPro's MSYS2 git comes first on PATH. It calls `cmd.exe` by full path too
(`C:\Windows\System32\cmd.exe`), never bare `cmd`: devkitPro's extensionless
`C:\devkitPro\msys2\usr\bin\cmd` shadows it in PowerShell and opens an "open with" popup.

## The disc in a sandbox

Unit tests and CI don't need it. Builds do (the translator reads `1ST_READ.BIN`), and so do boot runs.
Track 3 is over the 400 MB copy limit, so split it on the PC in a scratch folder outside `Game Files\`,
through folder access or in Git Bash through Remote Control
(`split -b 300M -d "Track 3.bin" track3.part.`), copy the parts, rejoin them in the sandbox
(`cat track3.part.* > "Track 3.bin"`), and run `scripts/00_verify_inputs.sh`. Delete the parts from the
PC afterwards (approved, `docs/decisions.md`), and never touch the disc files themselves. Everything from
the disc stays in that sandbox.

## Trying an unpushed dream-recomp change

`third_party/dream-recomp` is read-only, and `01_fetch_dream_recomp.sh` refuses it with local changes.
To build the game on a dream-recomp change before it's pushed, commit it in your own dream-recomp clone,
then build with `DREAM_RECOMP_URL=/path/to/that/clone` and its commit's full hash in
`data/dream-recomp.pin`. That pin edit is local only: it's committed here only after the dream-recomp
commit is pushed, as the pin move. A report on such a build names the dream-recomp commit it ran on.

## Building

1. `scripts/00_verify_inputs.sh DISC_FOLDER`. A mismatch means a different release: stop and tell me.
2. `scripts/01_fetch_dream_recomp.sh`.
3. `python3 scripts/02_make_gdi.py CUE games/jgr/disc.gdi` and
   `python3 scripts/03_get_boot_file.py games/jgr/disc.gdi games/jgr/boot/1ST_READ.BIN`.
4. `scripts/10_build_linux.sh` and `scripts/11_build_windows.sh`. Each takes about 15
   minutes: the translator re-emits 81 MB of C++ in one unit. That's longer than a cloud agent's
   foreground command limit, so run each in the background with its output in a log file
   (`scripts/10_build_linux.sh > build-linux.log 2>&1`), and wait for it to finish. A command that
   timed out isn't a failed build: read the log, and never start a second build over a running one.
   The 10-minute runs take about 6 minutes each and go in the background the same way.

Test builds keep the interpreter fallback (`DREAM_DEV_INTERPRETER=ON`), so a missed call shows up in the
report instead of stopping the game. A release drops it only once my play logs show 0 untranslated
calls (`docs/release-checklist.md`, step 2).

Windows builds always use `-mfma`, set by dream-recomp's toolchain file. MinGW-w64's `fmaf` isn't fused,
and it made Windows drift from Linux at frame 51, so a MinGW build without FMA doesn't compile.

## Before a commit

**In Jet Set Recomp:** `python3 scripts/audit_repo.py . --commits HEAD` reports CLEAN,
`python3 scripts/check_docs.py .` reports OK,
`python3 -m unittest discover -s tests` passes, and `bash -n` and `shellcheck` pass on every script. The
docs check follows the documents' pointers: links, quoted section names, the pin in its three places,
commit hashes, and the status file's size. Give it `--dream PATH`, a dream-recomp clone with full
history, or it only counts the hashes that are dream-recomp's; and in a project thread give it
`--shared FOLDER`, to check `known-bugs.md` against the files in `known-bugs/`. The
audit checks names only with a denylist: in a sandbox, write the maintainer's name to
`.git/info/audit-denylist` (never a tracked file); CI reads it from the `AUDIT_DENYLIST` secret.
`.github/workflows/ci.yml` runs the same on GitHub, which has no disc. In a clone of this repo,
`scripts/08_git_setup.sh` also installs three hooks: `pre-commit` runs the file audit on the staged files,
and `commit-msg` checks the message for a session link or a denied word
(`audit_repo.py . --message FILE`), so a leak is stopped before a push publishes it; CI would catch it
only after. The commit hooks can't check the author, committer or signature, which exist only once the
commit is made, so the `--commits HEAD` audit still runs. `pre-push` (`scripts/check_push.py`) refuses a
push of anything but `main`, one that isn't a fast-forward, one made while
`release-prep/RELEASE-IN-PROGRESS.md` is in the shared folder (it says so when it can't see the folder,
and goes on), and one whose commits don't pass the audit, each commit's files included. A hook stops a
slip, not a decision: `--no-verify` passes it over. A hook that isn't ours is left alone and named. A
thread that changes only docs or scripts needs shellcheck alone (`apt-get install shellcheck`, which section 4 allows), not the
toolchain and SDL3 builds of `scripts/09_setup_sandbox.sh`.

**In dream-recomp:** on the exact tree, on Linux:

- `cmake -S . -B build -DDREAM_RENDERER=ON && cmake --build build --parallel && ctest --test-dir build --output-on-failure`,
  and the headless configuration (`-DDREAM_RENDERER=OFF -DDREAM_DEV_INTERPRETER=ON`) as its CI does;
- clang-format 20.1.7, with the file list in its `.github/workflows/ci.yml`;
- the Windows cross-build (`docs/dev-setup.md` there).

**For anything the game runs:** the regression gate against the build before the change, and for a pin
move every 10-minute run in `data/baseline.json` too, the card runs included.

## The regression gate

dream-recomp's `tools/regress/gate.py`, which runs a 40 s attract and a 40 s gameplay scenario and, since
pin `98bb9fa`, the maintainer's recorded play-through as a third (`--replay NAME FILE SECONDS`), and
compares write hashes and counters. The play-through is recording 1 of 8 November, the Garage tutorial,
mission 1 and the Monster of Kogane: 1,325 s of guest time on a new memory card, a few frames past where
the maintainer closed the window, and about 13 minutes of host time in the sandbox:

```sh
G=third_party/dream-recomp/tools/regress/gate.py
R="--replay tutorial_mission1_kogane $PWD/data/recordings/2026-11-08-tutorial-mission1-kogane.txt 1325"
python3 $G capture before --build "$PWD/build" --config "$PWD/games/jgr/jgr.toml" --game jgr $R
# change, rebuild
python3 $G capture after --build "$PWD/build" --config "$PWD/games/jgr/jgr.toml" --game jgr $R
python3 $G compare before after
```

The gate measures guest writes only. It doesn't see drawing, sound or pacing, so a fix there shows
"identical" whether it worked or not. Such a fix needs its own test (for the renderer, a dream-recomp
unit test on a synthetic TA list, with no game art), and its report says the gate doesn't cover it.
Every drawing feature that's fixed or added gets one such test, shadows included. The gate and the
baseline cover the attract loop, the first 40 s of gameplay and recording 1's play-through, and a report
says so when the change reaches further. Every capture passes the `--replay` line above, so a compare
never reports that scenario MISSING. Captures made before 8 November ran the 5 November recording as
`tutorial_mission1` instead; it stopped fitting the game at pin `3023c32` (known bug 40), so they aren't
compared with newer ones on that scenario. Recording 2 (Shibuya-cho, 10 minutes) starts from the
maintainer's save, which never goes in a repo, so it isn't in the gate: it stays in the shared folder's
`recordings/` and is replayed by hand from that save (the maintainer, 8 November).

A changed hash is a fact, and whether it matters is a judgement: explain it in the report, and the
judgement is mine. A pin move or a phase exit whose gate shows a changed hash waits for my acceptance of
the explanation, however good it is (a pre-approved thread stops there, section 5). Captures are
keyed to one disc, build and platform: compare only captures made the same way, which is what the
manifest below records. A Windows or Wine capture is never compared with a Linux one.

Captures and write hashes outlive a sandbox in the shared folder's `captures/<commit>-<pin>/`, where
`<commit>` is this repo's commit and `<pin>` the first 7 digits of the pin. They hold hashes and counts
only, never screenshots, logs with instruction text or anything else from section 3's list. Each
folder has a `MANIFEST.txt`: the commit, the full pin, the SHA-256 of every file in `scripts/`, the
`clang --version` line, the date, and the commands run. Before building the before-build for a gate
run, look there for its captures. Reuse them only when the manifest matches exactly and they were made
on a Linux sandbox, and say in the report which you reused.

## The 10-minute runs

All headless, with `--rtc-seed 1 --max-seconds 600 --report FILE --write-hash FILE`:

- **No input.**
- **Presses:** `--press start@1500,start@1800,a@2100,start@2400,a@2700,a@3000,start@3300`.
- **The same two with a memory card:** `--vmu FILE`, naming a file that doesn't exist yet, so the
  program makes a blank, formatted card, as every player's first run does. The attract loop reads the
  card and takes code the no-card runs never reach: 0 untranslated targets since the pin `b222a6a`
  (6 November); the pin before it had 2 there, bug 11's cause B in `known-bugs.md`.

Compare each with its run in `data/baseline.json` (`no_input`, `presses`, `no_input_vmu`, `presses_vmu`).
The baseline's fifth run, `tutorial_mission1_kogane_replay`, is the maintainer's recording 1, the gate's
play-through: `--replay-input data/recordings/2026-11-08-tutorial-mission1-kogane.txt --rtc-seed 1
--max-seconds 1325 --vmu FILE` (a file that doesn't exist yet), about 13 minutes in a sandbox; a change
that reaches past the attract loop runs it too and compares the same way. Frames, traps, unmapped accesses and untranslated call targets must match or be explained; those are
the report's own lines, and it has no "faults" line, so a report never states a faults count it didn't
read. A clean run has 0 traps, 0 unmapped, and the untranslated count and addresses its baseline run
records: 0 without a card.

Speed is the sandbox's stand-in for the performance bar: each run's real-time multiple, compared with
`linux_sandbox_speed_x`. A run whose entry has `null` there was first made on the Windows PC (the card
runs, 5 November, at `windows_pc_speed_x`); the first Linux sandbox to make it records the number, with
my approval, and until then its speed isn't compared. Sandboxes differ by about 6% on the same build (1.6x and 1.7x), so a drop of
more than 15% is a finding that must be explained, and anything smaller is noise. It isn't the Ally X:
only a device step there shows the real bar.

`python3 scripts/30_compare_runs.py RUN=REPORT ...` makes the comparison: it reads each report's own
lines, prints one table against `data/baseline.json`, and exits 1 on a count that differs, a run that
didn't stop at its time limit, or a speed more than 15% under the baseline's. `--dir FOLDER` reads
`FOLDER/RUN.report.txt` for every run, `--all` makes a run with no report a finding, as a pin move
needs, and `--speed none` leaves speed out when the runs shared the machine with other work, which the
report then says. Its table goes in the report. What a difference means is still explained by hand.

`data/baseline.json` changes only with my approval.

## Delivery

One folder per build, named `<date>-<commit>-pin-<pin>-<topic>`, where `<pin>` is the first 7 digits
of the dream-recomp commit it was built on, so a build on an unpushed dream-recomp change says
which. It's made new with `scripts/20_package.sh`, which refuses a folder that isn't empty and an
SDL3 library with no sound system in it (`scripts/21_check_sdl_audio.py`: SDL3 opens ALSA, PulseAudio
and PipeWire at run time, so one built without their headers is silent without a word, known bug 21;
`scripts/09_setup_sandbox.sh` installs the headers and runs the same check on what it built). The
package as the sandbox makes it holds no disc file and no boot file, because nothing from the disc
leaves the sandbox; `setup.sh` or `setup.bat` makes those from the disc, and `copy-disc.sh` copies
the disc in first.

A test build plays out of the box (the maintainer, 5 Nov): what the maintainer receives carries
their save, `vmu-a1.bin`, the one furthest through the game, never an empty card, and needs no setup
beyond their game files. The save lives on the PC, so the build is packed with it there through
Remote Control, or the save is copied from the PC into the sandbox that packs it. On the PC, the
Windows folder in `Building\` is set up in place, with the disc where it is, so `play.bat` is the
only step. The Ally X build carries everything but the game files, which are too large to ship: the
maintainer copies the disc to the Ally X themselves and runs the package's `copy-disc.sh` once, in
Desktop Mode, naming the `.cue`; it copies the tracks into `disc/`, checks them against the hash
list, and writes `disc.gdi` with paths inside the folder, so the folder is complete and `play.sh`
can be added to Steam. The build's `TESTING.md` gives the steps.
Its launchers write a run log for every run, `logs/run-<start time>.txt`, and never overwrite one.
`play.sh` also keeps what the program prints on stderr in `logs/stderr-<start time>.txt`, because
Game Mode has no terminal, and names it in `logs/launcher.txt` when the program fails. The Windows
package carries `record.bat`, which records a play-through (`--record-input`, `--rtc-seed 1`) on a
copy of the save and keeps an untouched copy of the card it started from, which the replay needs.

- **Linux:** attached in the thread as a file, for the Ally X, or copied from the PC with the game
  files. I send its run logs back in the thread.
- **Windows:** stays on my PC in `Building\`, and you read its run logs there. If it's cross-built in
  the cloud, it's copied over once the PC is free.
- **Never published,** in any form, and no build goes to anyone else.

Before a build is delivered, test the package as delivered, not only the program:

1. Unpack a copy into an empty folder and run its own `setup.sh` (or `setup.bat`) with the disc's
   `.cue`. Setup writes disc files, so a Linux package is sent from the untouched original. A Linux
   package's `copy-disc.sh` is covered by the unit tests with a made-up disc, and by the Ally X steps.
2. From that folder, make `logs/` (without it the program writes no report and still exits 0,
   `known-bugs.md` 15), then run the program headless for 10 s with the launcher's files and a new card:
   `./jgr_boot --config jgr.toml --vmu logs/smoke-card.bin --max-seconds 10 --report logs/smoke.txt`
   (`jgr_boot.exe` on Windows). The card is a file that doesn't exist yet, as in the baseline's card
   runs, so the comparison below holds; the maintainer's save is never run in a test, and a package
   that carries it is smoked before the save goes in or on a copy without it.
3. Confirm the log exists and has 0 traps and 0 unmapped, and report its counts. Compare its
   untranslated call targets with the baseline's card runs (`no_input_vmu`): the same addresses are
   expected, and a new one is a finding.

Step 2 runs the program itself, not `play.sh` or `play.bat`, which force `--window`. The launchers are
covered by the unit tests, with a stand-in program, and by the device steps, so a sandbox report
doesn't call them tested end to end.

On the Ally X, `copy-disc.sh` (or setup) runs in Desktop Mode, from a terminal (Konsole). Game Mode has
no terminal: there, the game starts from `play.sh`, added to Steam as a non-Steam game. `TESTING.md`
steps say which mode.

Linux is checked this way in the sandbox. Windows is checked the same way on the PC through Remote
Control, with `setup.bat`, before I test. A build packed with the save is checked after packing: the
save's SHA-256 against its source, and the archive's listing (the package's modes and symlinks
kept). A package that fails any step isn't delivered.

Check each package's SHA-256 after every copy. With each build, write `TESTING.md`:

- what it is, what it's built from (commits, pin, toolchain, machine), and what was checked;
- numbered steps for what the change touches, each saying what to do, on which device, and what I'd
  see if it works and if it doesn't;
- which recorded run (`--record-input`) passes each step, or that I test it by hand;
- what to send back: the results, and every run log.

One platform at a time, and after any fix, rerun the passed steps it could affect.

## Reports

Every report on something the game runs states the commands run, the counts as the report prints them
(frames, traps, unmapped accesses, untranslated call targets), and the diff against `data/baseline.json`
and the gate. A change report also has: the root cause and its model, the code's history, files
touched, the regression test and that it fails without the fix, each hook's reason, docs updated,
platforms built or verified, what to test, and what's unverified.

## Review pack

Everything I need to approve one commit, in one `REVIEW.md` in the shared folder: the commit and the
`origin/main` it goes on, the testing per step and device, and the six checks of `docs/project-rules.md`
with each result. In a pre-approved thread it's the commit's record, and says under which pre-approval
it was made.
