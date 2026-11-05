# Status

The project's durable notes: where the work stands and what's next. Keep this current. Updated 5
November 2026. Reports and reasons: [test-boot-2026-11-04.md](test-boot-2026-11-04.md),
[decisions.md](decisions.md).

## Where it stands

- **Both repos are set up.** `spriteice/dream-recomp` carries our fixes on `main`: the four up to the pin
  in `data/dream-recomp.pin` (`6c098df`), which this repo builds on, then `697bfc8` (each block's exit
  written once, `known-bugs.md` 13) and `cdd66be` (dcdisc across drives, 14), both pushed 5 November
  and not pinned here yet. The first build from this repo matches `data/baseline.json` on both
  10-minute runs.
- **The game is playable on Windows.** The maintainer played build `2026-11-05-e06a4f9-pin-2013fb7`
  (named with old hashes, `docs/commit-map.md`) on the PC on 5 November: music, saving, loading, the
  tutorial and entering the first level work. Its run
  log showed 12,747 frames over 212 s at 1.0x, 0 traps, 0 unmapped, and 256 untranslated call targets
  that ran interpreted (`known-bugs.md`, 11).
- **Drawing has open bugs:** missing shadows, flickering character textures, rail depth, two wrong
  textures, sparks that don't follow the skates, and pacing while unfocused. `known-bugs.md` in the
  shared folder lists them.
- **SteamOS hasn't run anything yet.** Four Linux packages are in the shared folder's `builds/`: the
  current one is `2026-11-05-de56e83-linux`, and the two `depthfix-test` ones carry an unpushed
  dream-recomp change.

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
`reviews/recomp-work-order-2026-11-05.md` in the shared folder, and `release-prep/roadmap.md` there
puts each milestone in its phase.

1. **Map the code (now):** a full coverage pass, before any renderer work.
   - Entry: bug 11's three dream-recomp fixes (`known-bugs.md`, 11) rechecked, committed and pinned.
   - Work: a coverage report from the translator over the whole image, with every byte classed as
     function code, data or literal pool, switch table, padding, or unknown (the baseline leaves
     230,602 of 1,447,388 bytes undecoded), and every indirect jump and call site (`jmp`, `braf`,
     `jsr @Rn`, `bsrf`) classed as a recovered switch, a tail call or a resolved call. Discovery's
     200-instruction window fixed in the translator, with a test. Config seeds only where measured.
     The run log's own bugs fixed first, because the pass measures with it (`known-bugs.md`, 12 and
     15). The maintainer records at least two play-throughs with `--record-input` (the tutorial and the
     first stage, 5 minutes or more), added to the gate as its third scenario and to
     `data/baseline.json`.
   - Exit: every unknown range explained or translated, and listed with its size; no indirect jump
     site unclassified; both recorded runs show 0 untranslated calls, 0 traps and 0 unmapped
     accesses; the gate and both 10-minute runs match `data/baseline.json`, or the maintainer
     approves the new counts.
   - If the pass needs more than about ten re-emits, splitting the generated unit (phase 6) moves
     here. It's a restructure with no change in behaviour, shown by an identical gate.
2. **Tell translation faults from renderer faults.**
   - Entry: phase 1's exit, and recorded runs that reach each drawing bug's spot: the Shibuya
     Terminal road, the Garage, a grind, and sparks.
   - Work: replay each recorded run translated and with `--interpret`, and compare the per-frame write
     hashes and the TA capture at each bug's spot. A match puts the bug in the renderer. A difference
     puts it in translation, and it goes back to phase 1 with a test.
   - Exit: every recorded run's write hashes match the interpreted run's, or each difference is
     explained; bugs 5, 7, 8 and 9 each say "translation" or "renderer" in `known-bugs.md`.
   - Not measured yet: how long `--interpret` takes over a 5-minute recorded run.
3. **Runtime and platforms.**
   - Entry: phase 1's exit. The first SteamOS smoke test can run any time, since it changes no code.
     The next Linux build's `TESTING.md` has a step to start `play.sh` in Game Mode before setup, to
     see that its error dialog shows.
   - Work: pacing while unfocused (`known-bugs.md`, 10), and the sparks (9) if phase 2 puts them in
     game timing. SteamOS in Desktop Mode and Game Mode. Sound through a device, a controller, and a
     30-minute session.
   - Exit: bug 10 fixed with a test; a recorded run replays on the Ally X in Game Mode with 0 faults;
     presented frames per second logged with the window focused and unfocused.
4. **The renderer, one hardware feature at a time.** Each fix gets a unit test on a synthetic TA list
   that fails without it, because the gate doesn't see drawing, and a device step at the spot.
   - Entry: phase 2 has put the bug in the renderer, and phase 3 has fixed pacing.
   - Order: depth for the translucent list first (`known-bugs.md`, 6; the paused fix and its tests are
     in the shared folder's `depth-fix/`, to re-test on phase 1's function boundaries). Then modifier
     volumes (shadows, 1), because their stencil pass reads the depth that bug 6's fix changes; the
     game uses them in every 3D frame (39 opaque and 1 translucent in the last frame of w1). Then
     texture formats and palettes (7, 8), the texture cache (5), and the sparks (9) if they're the
     renderer's.
   - Exit: bugs 1 and 5 to 9 fixed and passed on both devices, each with a pixel count on a capture
     (the method in `depth-fix/diagnosis.md`).
5. **The whole game.**
   - Entry: phases 1 to 4.
   - Work: every stage played on both devices and recorded, each recording added to the gate. A new
     untranslated call goes back to phase 1, and a new drawing bug to phase 2.
   - Exit: every stage with 0 faults and 0 untranslated calls; then releases drop the interpreter
     fallback (`docs/decisions.md`); full speed with headroom measured on the Ally X in Game Mode.
6. **Speed, OpenGL and release.** Rebuild cost, unless phase 1 took it: each config change re-emits
   81 MB of C++ in one unit and takes about 15 minutes. OpenGL 3.3 core, as its own milestone. The
   release checklist (`docs/release-checklist.md`). Any enhancements the maintainer wants come last.

## Things that bite

- The PC's `git` on PATH is devkitPro's; use Git for Windows by full path. Bare `cmd` in PowerShell
  finds devkitPro's extensionless `cmd` and opens an "open with" popup; use
  `C:\Windows\System32\cmd.exe`. There's no `gh`, clang, ninja or clang-format on the PC, and none
  may be installed without asking.
- `jsrf-build` in WSL on the PC belongs to another project.
- Git Bash on the PC runs `scripts/00_verify_inputs.sh` fine.
- Hashing the whole disc takes about 5 minutes on the PC.
- `jgr_boot --window` opens a real window, and implies sound unless `--no-audio` is given.
