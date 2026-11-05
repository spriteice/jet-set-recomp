# Status

The project's durable notes: where the work stands and what's next. Keep this current. Updated 5
November 2026. Reports and reasons: [test-boot-2026-11-04.md](test-boot-2026-11-04.md),
[decisions.md](decisions.md).

## Where it stands

- **Both repos are set up.** `spriteice/dream-recomp` carries our four fixes on `main`, and this repo
  builds on it at the pin in `data/dream-recomp.pin` (`6c098df`). The first build from this repo matches
  `data/baseline.json` on both 10-minute runs.
- **The game is playable on Windows.** The maintainer played build `2026-11-05-e06a4f9-pin-2013fb7` on
  the PC on 5 November: music, saving, loading, the tutorial and entering the first level work. Its run
  log showed 12,747 frames over 212 s at 1.0x, 0 traps, 0 unmapped, and 256 untranslated call targets
  that ran interpreted (`known-bugs.md`, 11).
- **Drawing has open bugs:** missing shadows, flickering character textures, rail depth, two wrong
  textures, sparks that don't follow the skates, and pacing while unfocused. `known-bugs.md` in the
  shared folder lists them.
- **SteamOS hasn't run anything yet.** The first Linux package is in the shared folder's `builds/`.

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

In order. `release-prep/roadmap.md` in the shared folder has the milestones.

1. **Untranslated calls from play:** feed the played run's 256 targets to `--suggest-config`, and
   check each new entry with the gate (`known-bugs.md`, 11).
2. **SteamOS.** Nothing has run on the Ally X yet; the package in `builds/` is the first to try.
3. **Renderer bugs** (`known-bugs.md`, 5 to 8): each needs its own test, because the gate doesn't see
   drawing.
4. **Playing a stage:** a press script or recording that steers, and the gate's gameplay scenario pointed
   at it.
5. **Modifier volumes (shadows):** a stencil pass in dream-recomp's Vulkan renderer. The game uses them
   in every 3D frame (39 opaque and 1 translucent in the last frame of w1).
6. **Rebuild cost:** each config change re-emits 81 MB of C++ in one unit and takes about 15 minutes.
7. **OpenGL 3.3 core,** later, as its own milestone.

## Things that bite

- The PC's `git` on PATH is devkitPro's; use Git for Windows by full path. There's no `gh`, clang,
  ninja or clang-format on the PC, and none may be installed without asking.
- `jsrf-build` in WSL on the PC belongs to another project.
- Git Bash on the PC runs `scripts/00_verify_inputs.sh` fine.
- Hashing the whole disc takes about 5 minutes on the PC.
- `jgr_boot --window` opens a real window, and implies sound unless `--no-audio` is given.
