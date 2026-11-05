# Build and test reference

How builds of Jet Set Recomp are made, checked, delivered and reported. It's written by the maintainer
("I"), who never builds by hand and only runs what's delivered, for whoever makes them ("you").

## Test devices

- **Windows:** desktop PC, Windows 11, i7-10700K, 32 GB, RTX 2080 Ti.
- **Linux:** ROG Xbox Ally X on SteamOS. Builds must work in Desktop Mode and Game Mode (gamescope).

## Where the work runs

- **The cloud,** a thread's sandbox: code, checks, Linux builds, Windows cross-builds, and every commit
  and push. The tools section 4 of the instructions lists may be installed there
  (`scripts/09_setup_sandbox.sh`).
- **My PC,** through Remote Control and only for what needs Windows itself, such as running a Windows
  build. Everything is under `E:\Games\Ports\jsr\DC`: the disc in `Game Files\Dreamcast\`, builds in
  `Building\`. Before anything heavy, read `E:\Games\Ports\jsr\PC-IN-USE.md`, add a row saying whether a
  window opens and for how long, and remove it when done. Nothing is installed, committed or pushed
  from there. The `jsrf-build` WSL distribution there belongs to another project: don't use it.

A session on the PC uses Git for Windows by full path (`C:\Program Files\Git\cmd\git.exe`), because
devkitPro's MSYS2 git comes first on PATH.

## The disc in a sandbox

Unit tests and repo builds don't need it; only boot runs do. Track 3 is over the 400 MB copy limit, so:
split it into parts on the PC, copy them, rejoin them, and run `scripts/00_verify_inputs.sh`. Deleting
the parts from the PC needs my permission. Everything from the disc stays in that sandbox.

## Building

1. `scripts/00_verify_inputs.sh DISC_FOLDER`. A mismatch means a different release: stop and tell me.
2. `scripts/01_fetch_dream_recomp.sh`.
3. `python3 scripts/02_make_gdi.py CUE games/jgr/disc.gdi` and
   `python3 scripts/03_get_boot_file.py games/jgr/disc.gdi games/jgr/boot/1ST_READ.BIN`.
4. `scripts/10_build_linux.sh` and `scripts/11_build_windows.sh`. Each takes about 15
   minutes: the translator re-emits 81 MB of C++ in one unit.

Test builds keep the interpreter fallback (`DREAM_DEV_INTERPRETER=ON`), so a missed call shows up in the
report instead of stopping the game. Whether a release drops it is an open decision.

Windows builds always use `-mfma`, set by dream-recomp's toolchain file. MinGW-w64's `fmaf` isn't fused,
and it made Windows drift from Linux at frame 51, so a MinGW build without FMA doesn't compile.

## Before a commit

**In Jet Set Recomp:** `python3 scripts/audit_repo.py . --commits HEAD` reports CLEAN, `python3 -m unittest
discover -s tests` passes, and `bash -n` and `shellcheck` pass on every script. The audit checks names
only with a denylist: in a sandbox, write the maintainer's name to `.git/info/audit-denylist` (never a
tracked file); CI reads it from the `AUDIT_DENYLIST` secret. `.github/workflows/ci.yml` runs the same
on GitHub, which has no disc.

**In dream-recomp:** on the exact tree, on Linux:

- `cmake -S . -B build -DDREAM_RENDERER=ON && cmake --build build --parallel && ctest --test-dir build --output-on-failure`,
  and the headless configuration (`-DDREAM_RENDERER=OFF -DDREAM_DEV_INTERPRETER=ON`) as its CI does;
- clang-format 20.1.7, with the file list in its `.github/workflows/ci.yml`;
- the Windows cross-build (`docs/dev-setup.md` there).

**For anything the game runs:** the regression gate against the build before the change, and for a pin
move the two 10-minute runs too.

## The regression gate

dream-recomp's `tools/regress/gate.py`, which runs a 40 s attract and a 40 s gameplay scenario and
compares write hashes and counters:

```sh
G=third_party/dream-recomp/tools/regress/gate.py
python3 $G capture before --build "$PWD/build" --config "$PWD/games/jgr/jgr.toml" --game jgr
# change, rebuild
python3 $G capture after --build "$PWD/build" --config "$PWD/games/jgr/jgr.toml" --game jgr
python3 $G compare before after
```

The gate measures guest writes only. It doesn't see drawing, sound or pacing, so a fix there shows
"identical" whether it worked or not. Such a fix needs its own test (for the renderer, a dream-recomp
unit test on a synthetic TA list, with no game art), and its report says the gate doesn't cover it. The
gate and the baseline cover the attract loop and the first 40 s of gameplay only, and a report says so
when the change reaches further.

A changed hash is a fact, and whether it matters is a judgement: explain it in the report. Captures are
keyed to one disc and build, so they aren't comparable across machines.

## The two 10-minute runs

Both headless, with `--rtc-seed 1 --max-seconds 600 --report FILE --write-hash FILE`:

- **No input.**
- **Presses:** `--press start@1500,start@1800,a@2100,start@2400,a@2700,a@3000,start@3300`.

Compare both with `data/baseline.json`. Frames, faults, traps, unmapped accesses and untranslated calls
must match or be explained. A clean run has 0 faults, 0 traps, 0 unmapped and 0 untranslated.

`data/baseline.json` changes only with my approval.

## Delivery

One folder per build, named `<date>-<commit>-<topic>`, made with `scripts/20_package.sh`.
It holds no disc file and no boot file; the player's setup makes those.
Its launchers write a run log for every run, `logs/run-<start time>.txt`, and never overwrite one.

- **Linux:** attached in the thread as a file, for the Ally X. I send its run logs back the same way.
- **Windows:** stays on my PC in `Building\`, and you read its run logs there. If it's cross-built in
  the cloud, it's copied over once the PC is free.
- **Never published,** in any form, and no build goes to anyone else.

Before a build is delivered, test the package as delivered, not only the program:

1. Unpack a copy into an empty folder and run its own `setup.sh` (or `setup.bat`) with the disc's
   `.cue`. Setup writes disc files, so a Linux package is sent from the untouched original.
2. From that folder, run the program headless for 10 s with the launcher's files:
   `./jgr_boot --config jgr.toml --vmu vmu-a1.bin --max-seconds 10 --report logs/smoke.txt`
   (`jgr_boot.exe` on Windows).
3. Confirm the log exists and has 0 faults, 0 traps and 0 unmapped, and report its counts.

Linux is checked this way in the sandbox. Windows is checked the same way on the PC through Remote
Control, with `setup.bat`, before I test. A package that fails any step isn't delivered.

Check each package's SHA-256 after every copy. With each build, write `TESTING.md`:

- what it is, what it's built from (commits, pin, toolchain, machine), and what was checked;
- numbered steps for what the change touches, each saying what to do, on which device, and what I'd
  see if it works and if it doesn't;
- which recorded run (`--record-input`) passes each step, or that I test it by hand;
- what to send back: the results, and every run log.

One platform at a time, and after any fix, rerun the passed steps it could affect.

## Reports

Every report states the commands run, the counts (frames, faults, unmapped accesses, untranslated calls),
and the diff against `data/baseline.json` and the gate. A change report also has: the root cause and its
model, the code's history, files touched, the regression test and that it fails without the fix, each
hook's reason, docs updated, platforms built or verified, what to test, and what's unverified.

## Review pack

Everything I need to approve one commit, in one `REVIEW.md` in the shared folder: the commit and the
`origin/main` it goes on, the testing per step and device, and the six checks of `docs/project-rules.md`
with each result. In a pre-approved thread it's the commit's record, and says under which pre-approval
it was made.
