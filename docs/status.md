# Status

The project's durable notes: where the work stands and what's next. Keep this current. Updated 6
November 2026. Reports and reasons: [test-boot-2026-11-04.md](test-boot-2026-11-04.md),
[decisions.md](decisions.md).

## Where it stands

- **Both repos are set up.** `spriteice/dream-recomp` carries our fixes on `main`, and the pin in
  `data/dream-recomp.pin` is `b222a6a` (6 November): the four up to `6c098df`, then `697bfc8` (each
  block's exit written once, `known-bugs.md` 13), `cdd66be` (dcdisc across drives, 14), and the seven
  of 6 November, approved on cards: bug 11's three translator fixes (`6c6cc9f`, `8e409b0`, `ab1faa7`),
  constant propagation past a reload (`ef7c0a6`, bug 17), discovery's blocks cut into basic blocks
  (`73018dc`, bug 19), the run log's output paths and physical addresses (`795dcb8`, bugs 12 and 15),
  and the window's controls recorded for the right frame (`b222a6a`, bug 18). The build on this pin
  matches `data/baseline.json` on all four 10-minute runs on every count, the two memory-card runs
  now at 0 untranslated call targets (from 2, bug 11's cause B). The gate's write hash changed from
  frame 83 on with identical counters: the interrupt is delivered at a different boundary of the re-cut
  code and nothing else moves (`review-packs/bug-11-translator/REVIEW.md` in the shared folder, "The
  frame-83 hash change"); the maintainer accepted it with the pin move on 6 November.
- **The disc is in a sandbox and the first play-through is recorded.** The maintainer's tutorial-and-
  mission-1 recording (`data/recordings/2026-11-05-tutorial-mission1.txt`, inputs only; the original
  and its report in the shared folder's `recordings/`) is 66,516 frames with 0 traps, 0 unmapped and
  0 untranslated, and replays headless on Linux with every count equal (64,933 sectors, 236 memory-card
  block writes) once its frame numbers are lowered by one, which the committed file is: the launcher
  that recorded it wrote each frame's line before reading the controls (bug 18, fixed in `b222a6a`).
  It is `runs.tutorial_mission1_replay` in `data/baseline.json`; the gate still runs its two 40 s
  scenarios only (phase 1's open item: a replay scenario in `tools/regress/gate.py`).
- **The game is playable on Windows.** The maintainer played build `2026-11-05-e06a4f9-pin-2013fb7`
  (named with old hashes, `docs/commit-map.md`) on the PC on 5 November: music, saving, loading, the
  tutorial and entering the first level work. Its run
  log showed 12,747 frames over 212 s at 1.0x, 0 traps, 0 unmapped, and 256 untranslated call targets
  that ran interpreted (`known-bugs.md`, 11).
- **Drawing has open bugs:** missing shadows, flickering character textures, rail depth, two wrong
  textures, sparks that don't follow the skates, and pacing while unfocused. `known-bugs.md` in the
  shared folder lists them.
- **SteamOS hasn't run anything yet.** Five Linux packages are in the shared folder's `builds/`: the
  current one is `2026-11-05-de56e83-linux`, two older ones named with old hashes, and the two
  `depthfix-test` ones, which carry an unpushed dream-recomp change. None has `copy-disc.sh` yet: the
  next Linux package is the first with it, and it goes to the Ally X with the maintainer's save, without
  the game files, which the maintainer copies and puts in place with that script
  (`docs/build-and-test-reference.md`, Delivery). The 1.2 GB `Building\2026-11-05-de56e83-linux-ready.tar`
  on the PC, made with the disc inside before the rule changed, isn't the route any more.

The two tables and notes below are the first Windows check, made on build 1 before this repo existed.

## Windows runs, 5 November 2026

On the i7-10700K and RTX 2080 Ti, in `Building\dreamcast-jgr-build1\`, with `--rtc-seed 1`. Headless:
`jgr_boot.exe --config jgr.toml --rtc-seed 1 --max-seconds 600 --report FILE --write-hash FILE`, with
`--press` for the second. Windowed: `--window --no-audio --max-seconds N --screenshot-at F`.

| Run | Kind | Frames | Faults, traps, unmapped, untranslated | Interrupts | Renders | Sectors | Non-zero samples | Speed |
|---|---|---|---|---|---|---|---|---|
| w1 | Headless, no input | 35,977 | 0, 0, 0, 0 | 228,345 | 17,927 | 26,023 | 21,975,158 | 2.4x |
| r10 | The same, cloud Linux, 4 Nov | 35,977 | 0, 0, 0, 0 | 228,345 | 17,927 | 26,023 | 21,975,158 | 1.7x |
| w2 | Headless, presses | 35,977 | 0, 0, 0, 0 | 237,943 | 17,927 | 26,392 | 25,017,321 | 2.7x |
| r11 | The same, cloud Linux, 4 Nov | 35,977 | 0, 0, 0, 0 | 237,943 | 17,927 | 26,392 | 25,017,321 | 1.9x |
| w3 | Vulkan window, 50 s, no input | 3,007 | 0, 0, 0, 0 | 15,108 | 1,442 | | sound off | 1.0x, vsync |
| w4 | Vulkan window, 95 s, presses | 5,705 | 0, 0, 0, 0 | 34,413 | 2,791 | | sound off | 1.0x, vsync |

- The Vulkan window ran on the RTX 2080 Ti at 640x480, with nothing on stderr.
- Viewed by Claude: w3's presented frame 2700 is the title screen, with logo and a 3D street. w4's frame
  5300 is the letterboxed in-engine city scene with the player's character. Both looked right, apart
  from the missing shadows. The screenshots stay on the PC.
- w1's and w2's write hashes are on the PC too, in `runs\2026-11-05\`. The Linux runs' hashes went with
  their sandbox, so the frame-for-frame match with Linux was only ever shown for 90 s under Wine.

**Not checked:** sound through a device, a controller, long play, frame rate under load, and anything
past the TIME OVER screen.

## What's open

Six phases, in order, adopted by the maintainer on 5 November (`docs/decisions.md`). A phase ends only
when its exit is shown, with numbers. Work that changes no code, such as a device smoke test, can run
alongside. The reasons, from how other recompilation projects ordered their work, are in
`reviews/recomp-work-order-2026-11-05.md` in the shared folder, with the second pass of 6 November in
`reviews/recomp-work-order-second-pass-2026-11-06.md` there (the maintainer adopted its refinements,
`docs/decisions.md`), and `release-prep/roadmap.md` there puts each milestone in its phase.

1. **Map the code (now):** a full coverage pass, before any renderer work.
   - Entry: done 6 November. Bug 11's three dream-recomp fixes (`known-bugs.md`, 11) rechecked,
     committed and pinned, with two more discovery fixes the pass found (17, 19).
   - Work: a coverage report from the translator over the whole image, with every byte classed as
     function code, data or literal pool, switch table, padding, or unknown. The image is 3,075,648
     bytes, and discovery at the pin classes 1,216,786 of them as code (39.6%); the baseline's
     `bytes_total`, 1,447,388, is the span of the emitted functions, not the image
     (`bug11/RECHECK-HANDOFF.md`, finding D), so the pass measures against the image. Every indirect
     jump and call site (`jmp`, `braf`, `jsr @Rn`, `bsrf`) classed as a recovered switch, a tail call
     or a resolved call. A miss that discovery's own rules caused is a translator fix with a test, as
     bug 11's three were; config seeds only for what no rule could find, and only where measured.
     The run log's own bugs fixed first, because the pass measures with it (`known-bugs.md`, 12 and
     15). The maintainer records at least two play-throughs with `--record-input` (the tutorial and the
     first stage, 5 minutes or more), added to the gate as new scenarios and to
     `data/baseline.json`.
   - Exit: every unknown range explained or translated, and listed with its size; no indirect jump
     site unclassified; both recorded runs show 0 untranslated calls, 0 traps and 0 unmapped
     accesses; every 10-minute run in `data/baseline.json` matches it, or the maintainer approves
     the new counts; the gate's counters are equal, and its hash change (the bug 11 patches change
     the write hash from frame 83 on) is explained and accepted by the maintainer.
   - Where the exit stands (6 November, `coverage/coverage-report-2026-11-05.md` and
     `coverage/unknown-ranges.csv` in the shared folder): every byte of the image classed
     (1,263,576 instructions, 230,802 literal words, 14,786 switch-table words; 9,737 unknown ranges
     listed with their sizes, 15,452 bytes of them code-like and none referenced by any image word);
     every indirect site classed (257 switch tables, 724 resolved at run time through the function
     table, 4 out of image, which are the exception path's own jumps); one of the two recordings made
     and replaying with 0 untranslated, 0 traps, 0 unmapped; all four 10-minute runs match the
     baseline; the gate's hash change accepted. Open: the second recording (the first stage, 5 minutes
     or more) and the gate's replay scenario.
   - If the pass needs more than about ten re-emits, splitting the generated unit (phase 6) moves
     here. It's a restructure with no change in behaviour, shown by an identical gate.
2. **Tell translation faults from renderer faults.**
   - Entry: phase 1's exit, and recorded runs that reach each drawing bug's spot: the Shibuya
     Terminal road, the Garage, a grind, and sparks. The first recording (the tutorial in the Garage,
     mission 1 in Shibuya-cho) likely reaches all four: confirm that at the start rather than record
     more.
   - Work: replay each recorded run translated and with `--interpret`, and compare the per-frame write
     hashes and the TA capture at each bug's spot. A match clears the translator. A difference puts
     the bug in translation, and it goes back to phase 1 with a test.
   - What the oracle can't see: the interpreter is dream-recomp's own, built from the same decoder and
     instruction semantics as the translator (its ADR 2), so a match can't show a bug both share: a
     decoder table, an instruction's semantics, FPSCR mode handling. Those parts are what upstream's
     differential harness checks against Flycast's interpreter (its ADR 12; `docs/upstream.md`), so
     the risk is small, not zero. A match means "not the translator", not "the renderer": when a
     renderer fix in phase 4 doesn't move a bug, the next suspect is the shared CPU model, checked
     against Flycast, not a second renderer theory.
   - Exit: every recorded run's write hashes match the interpreted run's, or each difference is
     explained; bugs 5, 7, 8 and 9 each say "translation" or "renderer" in `known-bugs.md`.
   - Not measured yet: how long `--interpret` takes over the 1,109 s recording. The first thread with
     the pinned build and the recording measures it.
3. **Runtime and platforms.**
   - Entry: phase 1's exit. The first SteamOS smoke test runs now, on the pin-move build, which goes
     to both devices: a Windows build on the PC, and a Linux package with `copy-disc.sh` for the Ally X
     (the maintainer, 6 Nov 01:28). It changes no code, and nothing has run on SteamOS yet. That Linux
     build's `TESTING.md` has a step to start `play.sh` in Game Mode before setup, to see that its
     error dialog shows.
   - Work: pacing while unfocused (`known-bugs.md`, 10), and the sparks (9) if phase 2 puts them in
     game timing. SteamOS in Desktop Mode and Game Mode. Sound through a device, a controller, and a
     30-minute session.
   - Exit: bug 10 fixed with a test, and pacing measured on both devices, because it depends on the
     host (Zelda64Recomp was still fixing pacing fifteen months after its release); a recorded run
     replays on the Ally X in Game Mode with 0 traps and 0 unmapped accesses; presented frames per
     second logged with the window focused and unfocused, on both devices. Phase 5 re-measures pacing
     on every stage.
4. **The renderer, one hardware feature at a time.** Each fix gets a unit test on a synthetic TA list
   that fails without it, because the gate doesn't see drawing, and a device step at the spot. Where
   one fits, the list comes from a KOS `pvr` example: open source, no game data, and what dream-recomp
   measures its own renderer against, with Flycast's PVR test scenes (its WP2.3).
   - Entry: phase 2 has put the bug in the renderer, and phase 3 has fixed pacing. For each bug, a
     reference frame at its spot from the disc running on Flycast or a Dreamcast, kept on the PC and
     never in a repo: without one, "fixed" means "looks right to us". And the run log says which
     renderer path each device takes, per-pixel or per-strip (dream-recomp's ADR 9: the per-pixel path
     needs GPU features, so the fallback stays), because the RTX 2080 Ti and the Ally X may run two
     paths, and a fix has to be right in both.
   - Order: depth for the translucent list first (`known-bugs.md`, 6; the paused fix and its tests are
     in the shared folder's `depth-fix/`, to re-test on phase 1's function boundaries). Then modifier
     volumes (shadows, 1), because their stencil pass reads the depth that bug 6's fix changes; the
     game uses them in every 3D frame (39 opaque and 1 translucent in the last frame of w1). Then
     texture formats and palettes (7, 8), the texture cache (5), and the sparks (9) if they're the
     renderer's.
   - Exit: bugs 1 and 5 to 9 fixed and passed on both devices, each with a pixel count on a capture
     (the method in `depth-fix/diagnosis.md`) and against its reference frame.
5. **The whole game.**
   - Entry: phases 1 to 4.
   - Work: first the acceptance matrix, a table of stage by device by mode (Windows; the Ally X in
     Desktop Mode and in Game Mode), so "done" is a count of green rows, as dream-recomp's own plan
     (its WP3.4) and other ports do. Then every stage played on both devices and recorded, each
     recording added to the gate, and pacing re-measured on each. A new untranslated call goes back to
     phase 1, and a new drawing bug to phase 2.
   - Exit: every row green, with 0 traps, 0 unmapped accesses and 0 untranslated calls on every stage;
     then releases drop the interpreter fallback (`docs/decisions.md`), and the release configuration,
     with the fallback off, passes the gate and the matrix too (upstream builds both configurations in
     CI so the fallback never becomes load-bearing); full speed with headroom measured on the Ally X in
     Game Mode.
6. **Speed, OpenGL and release.** Rebuild cost, unless phase 1 took it (it didn't: four full builds):
   each config change re-emits 81 MB of C++ in one unit and takes about 15 minutes. OpenGL 3.3 core, as
   its own milestone. The player's build: a release is source only, so the build is what a player
   gets, and today it runs on Linux alone (Windows is cross-compiled). Phase 6 adds a Windows-hosted
   build (MSVC or clang-cl, as upstream's own CI builds Windows x64), documented in the README, and a
   timed build from a clean checkout on both OSes by someone who isn't us, before the release
   checklist (`docs/release-checklist.md`) runs (the maintainer, 6 Nov 01:28). Any enhancements the
   maintainer wants come last.

## Things that bite

- The PC's `git` on PATH is devkitPro's; use Git for Windows by full path. Bare `cmd` in PowerShell
  finds devkitPro's extensionless `cmd` and opens an "open with" popup; use
  `C:\Windows\System32\cmd.exe`. There's no `gh`, clang, ninja or clang-format on the PC, and none
  may be installed without asking.
- `jsrf-build` in WSL on the PC belongs to another project.
- Git Bash on the PC runs `scripts/00_verify_inputs.sh` fine.
- Hashing the whole disc takes about 5 minutes on the PC.
- `jgr_boot --window` opens a real window, and implies sound unless `--no-audio` is given.
- The PC is shared with the JSRF-PC project (the maintainer, 5 November): one job runs on it at a
  time, and the claim lives in that project's shared folder at `building-on-pc/PC-IN-USE.md`, not in
  `E:\Games\Ports\jsr\`. Before any PC work: read it, and an "In use from ..." line means wait or
  work elsewhere; if it's free, add one line ("In use from <UTC time> on <date> by <project and
  thread>, <what and where>, about <how long>"); read it again just before starting; when done, move
  the line to the top of `PC-HISTORY.md` beside it. Stay out of `Claude\Building\` and the
  `jsrf-build` Docker setup. A thread that can't reach that folder asks the maintainer first.
