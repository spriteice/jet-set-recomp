# History

What was done and measured on the way to where [status.md](status.md) says the work stands. Nobody
has to read this file before working: it's where to look when a number, a build or a reason is
needed. The plan it follows is [plan.md](plan.md), who decided what is in
[decisions.md](decisions.md), and the first test boot's report is
[test-boot-2026-11-04.md](test-boot-2026-11-04.md).

Times are UTC unless marked UTC+8. This repository's history starts on 8 November 2026 with
`f9f84ae`, so a Jet Set Recomp hash from before that day, in a note or in the name of a build or a
capture folder, names a commit the repository no longer holds. Build names of 5 November also carry
`2013fb7`, dream-recomp's `6c098df` before that day's rewrite (`known-bugs.md`, 2).

## Log

Newest first. One dated entry for each thing done or measured: what, its numbers, and where its
evidence is. Everything below this section was `status.md`'s text on 14 November 2026, moved here
unchanged.

- **14 November 2026: the rules review, and the checks it added.** A review of the rules and the
  workflow ranked 11 changes, and the maintainer chose the seven that change no rule. What landed,
  each on a card ([decisions.md](decisions.md), 14 November) and each with its review pack in the
  shared folder's `review-packs/`:
  - `0f63b75`, the PC claim's steps in the maintainer's words (`rules-review-00-pc-claim-rule`).
  - `aaa4f15`, `7b36d64`, `a089e8d` and `cb49ea3`: six stale lines corrected; `status.md` split from
    33 KB into the state (3 KB), [plan.md](plan.md) and this file; the shared folder's
    `known-bugs.md` split from 59 KB into an index (9 KB) and one file for each of its 45 bugs; and
    the table in `CLAUDE.md` of what to read again, and when (`rules-review-01-tidy-up` to
    `rules-review-04-re-read-table`).
  - `4a81c8a`, `scripts/check_docs.py` and its CI step, and `39d1e38`, `scripts/check_push.py` as
    the pre-push hook: 18 tests, and CI run 11 passed (`rules-review-06a-docs-check`,
    `rules-review-06b-push-hook`).
  - `b6ce209`, `scripts/30_compare_runs.py`: 9 tests, and CI run 12 passed. On the real reports of
    the shared folder's `captures/2fa6456-6154c9a` it prints MATCH for 5 of 5 runs
    (`rules-review-04a-compare-runs`).
  - `3dec93a`, `scripts/review_pack.py`: 8 tests, and CI run 13 passed
    (`rules-review-08-review-pack`).
  - `eff3299`, `scripts/31_pin_check.py`: 15 tests, each of 94 one-line breaks of the script fails
    at least one of them, and CI run 15 passed (`rules-review-04b-pin-check`). It is **unverified on
    the game**: no sandbox had the disc, so it has never built the game, captured the gate on it or
    made a run. The first pin move that uses it makes the by-hand steps as well, and compares the
    two.

  The scripts' tests went from 57 to 107. None of it changes what the game runs, so no build, gate
  or 10-minute run was made for it.

## Where it stood on 14 November 2026

- **Both repos are set up.** `spriteice/dream-recomp` carries our fixes on `main`, and the pin in
  `data/dream-recomp.pin` is `6154c9a` (9 November): the four up to `6c098df`, then `697bfc8` (each
  block's exit written once, `known-bugs.md` 13), `cdd66be` (dcdisc across drives, 14), the seven
  of 6 November, approved on cards: bug 11's three translator fixes (`6c6cc9f`, `8e409b0`, `ab1faa7`),
  constant propagation past a reload (`ef7c0a6`, bug 17), discovery's blocks cut into basic blocks
  (`73018dc`, bug 19), the run log's output paths and physical addresses (`795dcb8`, bugs 12 and 15),
  the window's controls recorded for the right frame (`b222a6a`, bug 18), the gate's replay scenario
  (`98bb9fa`, tools only), the window's pacing dropping lost time instead of sprinting (`8df9635`,
  bug 22), a suboptimal swapchain image presented before the rebuild (`86e2b2a`, bug 23's candidate),
  three CI fixes (`a205ea9`, `45bbffe`, `782469f`: tests and the gate's launcher lookup, known bugs
  28 and 29), and four window fixes: a present semaphore per swapchain image (`c1016c5`, bug 25), a
  failed window stopping the run with its error (`da5830c`, 26), a staging buffer per frame in flight
  (`b76cc75`, 34), the vertical-blank hook holding its pacer instead of a dead local (`d990818`,
  35, the cause of 23's crash), and two floating-point fixes of 7 November: the runtime's own hooks
  and the run's end in the host's mode (`56a4277`, bug 37, so the run report rounds to nearest), and
  the game started in the mode the disc's bootstrap hands over, FPSCR `0x00040000`, round to nearest,
  where it was `0x00040001`, toward zero (`3023c32`, bug 36: the intro demo now matches Flycast step
  for step), then two more of 7 November: a return into the middle of a function resumes in the
  function that has a label there, through any address alias (`0204111`, bug 39), and the dev
  interpreter's log of every address it executes (`f8671ad`, `--exec-coverage`, a measurement tool,
  phase 1's check that no unknown byte executes), and one of 8 November: the windowed launcher drops
  the cached textures the game has written over in video memory before each render (`71d5a66`, bug
  41: the garage's graffiti preview kept the previous design), and one of 9 November: the presenter
  draws the picture only inside its own rectangle (`6154c9a`, bug 43: in a maximised or fullscreen
  window the picture's last column was smeared out to the window's edge and cut off by a black
  corner). The translator is `0204111`'s, which changes only what the resume switch matches. Bug
  36's fix changes the game's arithmetic, and the
  maintainer approved the new counts with this pin: the four 10-minute runs keep every count but
  interrupts and non-zero sound samples (35,977 frames, 0 traps, 0 unmapped, 0 untranslated each, the
  two memory-card runs at 0 untranslated since `b222a6a`, bug 11's cause B), and the gate's attract and
  gameplay scenarios changed hash and counters with it, at 0 traps, 0 unmapped, 0 untranslated. The
  recorded play-through no longer replays its recording (next point). The gate's write hash changed
  from frame 83 on at `b222a6a` with identical counters: the interrupt is delivered at a different
  boundary of the re-cut code and nothing else moves (`review-packs/bug-11-translator/REVIEW.md` in
  the shared folder, "The frame-83 hash change"); the maintainer accepted it with that pin move.
  Pin `f8671ad` changes no count of the four 10-minute runs, which equal the baseline on every line,
  sound samples included, nor of the gate's attract and gameplay scenarios, identical in hash and
  counters; the stale replay's untranslated call targets go from 1 to 0 (bug 39). Pin `71d5a66`
  changes nothing headless, where the launcher never drops a texture: the four 10-minute runs keep
  every count, each with the same write hash as at `3023c32`, and the gate's three scenarios are
  identical to `f8671ad`'s, write hash and counters. Pin `6154c9a` changes nothing headless either,
  where nothing is presented: the four 10-minute runs keep every count, each with the same write hash as
  at `71d5a66`, and the gate's three scenarios are identical to `71d5a66`'s, write hash and counters.
  Nothing is ahead of the pin on dream-recomp `main` (9 November, 02:50 UTC).
- **The disc is in a sandbox, and recording 1 is the baseline's and the gate's play-through.** The
  maintainer's recording 1 of 8 November (`data/recordings/2026-11-08-tutorial-mission1-kogane.txt`,
  inputs only; the original, the device's report and the sandbox's replay in the shared folder's
  `recordings/2026-11-08-tutorial-mission1-kogane/`) plays the Garage tutorial, mission 1 in Shibuya-cho
  with a save, the graffiti list and the Monster of Kogane, on a new card, on the Ally X in Game Mode
  with test build `2026-11-07-191c64b-pin-3023c32-test-linux`: 79,424 frames, 0 traps, 0 unmapped,
  0 untranslated, 212 card block writes. Replayed headless at pin `71d5a66` for 1,325 s of guest time,
  14 frames past the window's closing, it gives 79,438 frames, 0 traps, 0 unmapped, 0 untranslated and
  the device's card counts, every frame's write hash equal to its replay on the recording's own
  program, `3023c32`. It is `runs.tutorial_mission1_kogane_replay` in `data/baseline.json` and the
  gate's third scenario (`tutorial_mission1_kogane`, by `--replay`), whose write hash equals the
  baseline run's (the maintainer's cards "Yes, start now" and "Recording 1 only for now", 8 November).
  It replaces the 5 November recording (`data/recordings/2026-11-05-tutorial-mission1.txt`), made while
  the game rounded toward zero: since pin `3023c32` (bug 36's fix) its inputs stop fitting the game, and
  replayed, it reads unmapped memory from frame 52,858 (463,467,923 accesses, `known-bugs.md` 40) and
  never saves. Its file stays for bug 40's open check, and its old baseline entry is in the shared
  folder's `recordings/2026-11-05-tutorial-mission1/baseline-entry.json`. Recording 2 (the shared
  folder's `recordings/2026-11-08-shibuya-cho/`:
  Shibuya-cho for 10 minutes from the maintainer's save, 36,018 frames, 0 traps, 0 unmapped, and
  1 untranslated call target, bug 39, fixed at pin `f8671ad` after it was made) starts from that save,
  which never goes in a repo, so it stays out of the baseline and the gate and is replayed by hand from
  the save. Replayed at pin `71d5a66` from a copy of that save (8 November), it has 0 untranslated call
  targets, and every other count and every frame's write hash as on `3023c32` (the shared folder's
  `captures/ca289fc-71d5a66/recording2/`).
- **The game is playable on Windows.** The maintainer played build `2026-11-05-e06a4f9-pin-2013fb7` on
  the PC on 5 November: music, saving, loading, the tutorial and entering the first level work. Its run
  log showed 12,747 frames over 212 s at 1.0x, 0 traps, 0 unmapped, and 256 untranslated call targets
  that ran interpreted (`known-bugs.md`, 11).
- **Drawing has open bugs:** missing shadows, flickering character textures, rail depth, a wrong
  texture on the Shibuya Terminal road, and pacing while unfocused. `known-bugs.md` in the shared folder lists them. On the Ally X, the maintainer reports the
  Garage roof's wrong texture (8) gone, most likely with bug 41's fix (pin `71d5a66`), and the
  flickering character textures (5) and the road (7) still there (8 November). Phase 2's per-bug
  check put 7 in the renderer with its cause, and 5 there too with its cause on 10 November. The
  sparks that stay behind on a grind (9) are the game's own behaviour, and the bug is closed (the
  maintainer, 14 November).
  A maximised or fullscreen window drew the picture's edge out to the window's edge (43): fixed at pin
  `6154c9a`, and the maintainer saw it fixed on the Ally X and on Windows (9 November), with the test
  builds `2026-11-08-8661d09-pin-6154c9a-test-fullscreen-linux` and `-windows`, the first Windows
  build with bug 41's fix in it, where only the window was checked.
- **SteamOS runs it (6 November).** The Ally X first ran package
  `2026-11-06-179cdfd-pin-b222a6a-linux` (the first with `copy-disc.sh`, sent with the maintainer's save
  and no game files, as Delivery says) in Desktop Mode: 81 s of guest time in 89.6 s (0.9x), 4,892
  frames, 0 traps, 0 unmapped, 0 untranslated; and in Game Mode until it crashed (exit 139) when the
  Steam overlay opened: `known-bugs.md` 20 to 23, slow in Desktop Mode, no sound, too fast in Game
  Mode, and the crash. The test package `2026-11-06-ddb315d-pin-91c1638-test-window-linux` (this pin's
  code, and SDL3 with its sound headers) cleared all four on the device: Desktop Mode from Konsole, 55.543 s
  of guest time in 55.78 s (0.996 of real time, from 0.904); Desktop Mode through Steam, 0.954; Game
  Mode, 217.991 s in 220.60 s (0.988), 13,078 frames, the Steam menu opened and closed; each 0 traps,
  0 unmapped, 0 untranslated, with sound (0 samples dropped) and the controller. The crash was bug 35,
  the vertical-blank hook writing a dead local, not the swapchain. The run reports print those ratios
  as 0.9x: their decimals round toward zero under the guest's FPU mode (37). From Konsole the
  controller does nothing, as with other ports: Steam holds it in Desktop Mode (38). Open there: the
  drawing bugs above. The attract demo that played out of step (36) is fixed at pin `3023c32`, not yet
  seen on a device. The older Linux packages in the
  shared folder's `builds/` and the 1.2 GB `Building\2026-11-05-de56e83-linux-ready.tar` on the PC are
  superseded.

## Windows runs, 5 November 2026

The two tables and notes below are the first Windows check, made on build 1 before this repo existed.

On the i7-10700K and RTX 2080 Ti, in `Building\dreamcast-jgr-build1\`, with `--rtc-seed 1`. Headless:
`jgr_boot.exe --config jgr.toml --rtc-seed 1 --max-seconds 600 --report FILE --write-hash FILE`, with
`--press` for the second. Windowed: `--window --no-audio --max-seconds N --screenshot-at F`.

| Run | Kind | Frames | Traps, unmapped, untranslated | Interrupts | Renders | Sectors | Non-zero samples | Speed |
|---|---|---|---|---|---|---|---|---|
| w1 | Headless, no input | 35,977 | 0, 0, 0 | 228,345 | 17,927 | 26,023 | 21,975,158 | 2.4x |
| r10 | The same, cloud Linux, 4 Nov | 35,977 | 0, 0, 0 | 228,345 | 17,927 | 26,023 | 21,975,158 | 1.7x |
| w2 | Headless, presses | 35,977 | 0, 0, 0 | 237,943 | 17,927 | 26,392 | 25,017,321 | 2.7x |
| r11 | The same, cloud Linux, 4 Nov | 35,977 | 0, 0, 0 | 237,943 | 17,927 | 26,392 | 25,017,321 | 1.9x |
| w3 | Vulkan window, 50 s, no input | 3,007 | 0, 0, 0 | 15,108 | 1,442 | | sound off | 1.0x, vsync |
| w4 | Vulkan window, 95 s, presses | 5,705 | 0, 0, 0 | 34,413 | 2,791 | | sound off | 1.0x, vsync |

- The Vulkan window ran on the RTX 2080 Ti at 640x480, with nothing on stderr.
- Viewed by Claude: w3's presented frame 2700 is the title screen, with logo and a 3D street. w4's frame
  5300 is the letterboxed in-engine city scene with the player's character. Both looked right, apart
  from the missing shadows. The screenshots stay on the PC.
- w1's and w2's write hashes are on the PC too, in `runs\2026-11-05\`. The Linux runs' hashes went with
  their sandbox, so the frame-for-frame match with Linux was only ever shown for 90 s under Wine.

**Not checked:** sound through a device, a controller, long play, frame rate under load, and anything
past the TIME OVER screen.

## Phase 1

1. **Map the code (done 8 November):** a full coverage pass, before any renderer work.
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
   - Where the exit stands (7 November, `coverage/coverage-revision-2026-11-07.md` and
     `coverage/unknown-ranges-2026-11-07.csv` in the shared folder, revising the 5 November report):
     every byte of the image classed (1,263,576 instructions, 230,802 literal words, 14,786
     switch-table words; 9,739 unknown ranges listed with their sizes); 2,268 bytes once counted as
     code-like reclassed as float constants that decoded code loads through `mova`, leaving 13,184
     code-like bytes, 7,550 of them `nop` padding; none of them a branch or call target from known
     code, and none executed: the five baseline runs of 7 November and both recordings of 8 November,
     run fully interpreted with dream-recomp's `--exec-coverage`, execute 505,420 bytes of the image,
     every one a decoded instruction (368,578 for the five runs; the recordings in the shared folder's
     `mapping/measure/2026-11-08/`); every
     indirect site classed (257 switch tables, 724 resolved at run time through the function
     table, 4 out of image, which are the exception path's own jumps); all four 10-minute runs match the
     baseline; the gate's hash change accepted; the gate's replay scenario in since pin `98bb9fa`.
     The recordings: recording 1 of 8 November (the tutorial, mission 1 and Kogane, on a new card)
     is in the baseline and the gate, at 0 traps, 0 unmapped and 0 untranslated, in place of the
     5 November recording, which stopped fitting the game at pin `3023c32` (bug 36's fix; its unmapped
     reads are bug 40, and its one untranslated call target there, a non-local return into the middle
     of a function, is bug 39, fixed at pin `f8671ad`, `review-packs/dream-recomp-18-resume-labels/`).
     Recording 2 (Shibuya-cho, 10 minutes, from the save) stays out of both and is replayed by hand
     (the maintainer, 8 November). At pin `71d5a66` it replays with 0 untranslated call targets (bug
     39's fix), every other count and write hash as before. Both recordings, run interpreted with
     `--exec-coverage` at that pin, execute only decoded instructions (417,224 and 408,382 bytes of the
     image), with 0 traps, 0 unmapped and 0 untranslated. Recording 2's interpreted run plays the same
     game as its translated replay. Recording 1's makes the same 49 card block reads and 212 writes and
     then leaves the translated replay's path (68,791 GD-ROM sectors against 85,883; where, not
     measured), most likely because the interpreter takes interrupts at other instruction boundaries
     (bug 40's notes). So its interpreted run covers the tutorial, mission 1 and the save, not Kogane,
     which the translated replay runs with 0 untranslated call targets: only translated code ran there.
   - If the pass needs more than about ten re-emits, splitting the generated unit (phase 6) moves
     here. It's a restructure with no change in behaviour, shown by an identical gate.
   - Exited 8 November, on the maintainer's card "Close it, upstream check next" (9:21pm UTC+8),
     with every exit line met by the numbers above (the shared folder's
     `reviews/next-after-phase-1-2026-11-08.md`). Recording 1 alone meets the recordings item: it plays
     the tutorial and the first stage, which the two recordings were for. Bugs 24 (constant propagation;
     nothing in this game reaches it) and 40 (the stale 5 November recording only) stay open outside the
     exit. The phase-exit upstream check (`docs/upstream.md`) found upstream's `main` still at
     `51ca276`, our base, so there was nothing to merge.

## Phase 2

2. **Tell translation faults from renderer faults (done 14 November).**
   - Exited 14 November, on the maintainer's card "Close it, phase 3 next" (8:49am UTC+8), with
     both exit lines met (the shared folder's `reviews/phase-2-exit-2026-11-14.md`). Bugs 5 and 7 are
     the renderer's, with their causes; 9 is the game's own behaviour, closed by the maintainer; 8 is
     gone on the Ally X since bug 41's fix. Every write-hash difference between recording 1's
     translated and interpreted runs is explained, below, and none is a translation fault. Recording
     2's difference wasn't examined store by store: its interpreted run plays the same game, and both
     causes belong to the translated code and the interpreter, not to a recording. The phase-exit
     upstream check found upstream's `main` still at `51ca276`, so there was nothing to merge.
   - Entry: phase 1's exit, and recorded runs that reach each drawing bug's spot: the Shibuya
     Terminal road, the Garage, a grind, and sparks. The first recording (the tutorial in the Garage,
     mission 1 in Shibuya-cho) likely reaches all four: confirm that at the start rather than record
     more.
   - Work: replay each recorded run translated and with `--interpret`, and compare the per-frame write
     hashes and the TA capture at each bug's spot. A match clears the translator. A difference puts
     the bug in translation, and it goes back to phase 1 with a test.
   - What the oracle can't see: [plan.md](plan.md), phase 2.
   - Exit: every recorded run's write hashes match the interpreted run's, or each difference is
     explained; bugs 5, 7, 8 and 9 each say "translation" or "renderer" in `known-bugs.md`.
   - Measured on 8 November, at pin `71d5a66` in the sandbox: `--interpret` runs at 0.2x, 95 minutes
     for recording 1's 1,325 s and 44 for recording 2's 601 s (three runs at once on four cores).
     Recording 1's interpreted run leaves the translated replay's path in mission 1, after the save,
     between frames 50,100 and 50,400 (the per-bug check, below), most likely because the interpreter
     takes interrupts at other instruction boundaries, as bug 40's notes found the 5 November
     recording's two runs doing from frame 24.
   - Started 8 November with the per-bug check (the maintainer's card "Per-bug check first", 10:42pm
     UTC+8): no new code, recording 1 run translated and interpreted to the spots of bugs 5, 7 and 9,
     on one build and one renderer, in the sandbox with the disc. The two runs part on interrupt
     timing but play the same path up to the save, so a bug that shows in both at its spot isn't the
     translator's, and one that shows only translated goes back to phase 1 with a test. Bug 8 is gone
     on the Ally X (above), so it isn't placed this way. Upstream's save states, or the dev interpreter
     taking interrupts where translated code does, come on their own cards only if a bug can't be
     placed. The plan is the shared folder's `phase2/per-bug-check/PLAN.md`.
   - The per-bug check's result (8 November, the shared folder's `phase2/per-bug-check/FINDINGS.md`):
     run in the sandbox with the disc, on lavapipe, with a binary that adds only a screenshot switch
     to pin `71d5a66` and changes no count or write hash. Windowed, recording 1 draws pixel-identical
     frames translated and interpreted in all 1,708 screenshots up to frame 50,100, and differs in all
     410 from 50,400. The write hashes differ from frame 1, and the interpreted run has delivered 315
     fewer interrupts by frame 28,471, where both runs' display lists are still byte-identical: that
     difference is still to be shown at its write. Every run: 0 traps, 0 unmapped, 0 untranslated,
     the same memory-card counts, and the translated runs' write hashes equal the baseline replay's.
     - Bug 7 is the renderer's. Every polygon that uses a texture gets one sampler. Its clamp and
       flip come from the frame's last polygon on that texture, and the texture cache keeps that
       sampler across frames. On the console, clamp and flip are each polygon's own. At the bus
       terminal that clamps the near brick walkway into bars. Both runs show them there, and
       changing only that last polygon's TSP in a capture moves them. The fix is phase 4's.
     - Bug 5 is the renderer's (10 November). The 8 November check said the sandbox doesn't show it.
       That was wrong: it does, in both runs alike, and the check's detector missed it because it
       counted only pixels darker than the game's outline colour (34,0,2). The game draws its cel
       outline as a hull of translucent polygons around each character, and the hardware sorts
       translucent pixels by depth (auto-sort mode). The renderer sorts whole polygons by their
       nearest vertex instead (`Renderer::draw`), so wherever a hull polygon sorts after the model it
       covers it: the legs, skates and hands take the outline colour, and the order changes as the
       model moves. In a capture of Beat mid-grind the hull covers him at 1,622 of the 6,073 pixels
       where he's nearer, and moving only the hull earlier brings those parts back. Depth is ruled
       out. The maintainer's Ally X replay of recording 1 wrote the sandbox's hash on every frame to
       50,100 and showed the flashes throughout, as the Windows PC does. The check was the
       maintainer's card "Look now, no code" (6:06pm UTC+8); its results are the shared folder's
       `phase2/per-bug-check/results/03-bug5-cause.txt`. The fix is phase 4's: per-pixel sorting of
       the translucent list. The same check's validation run found a sync hazard on the window's
       depth image that changes nothing on screen (`known-bugs.md`, 45).
     - Bug 9 doesn't show in the sandbox as a fault: in every grind the newest sparks come from the
       skates, in both runs alike. The maintainer closed it on 14 November as the game's own
       behaviour.
   - The write-hash difference, shown store by store (10 November, the maintainer's cards "Write log,
     no code" and "Show frame 173 too, no code"; the shared folder's `phase2/hash-difference/`), with
     `--write-log` and `--mask-segment`:
     - Frames 1 and 2 differ only in bits 29 to 31 of 47 return addresses pushed to the stack
       (`0x0c...` translated, `0x8c...` interpreted), a false difference dream-recomp documents and
       masks with `--mask-segment`. Masked, the hashes are equal to frame 23.
     - From frame 24, the first interrupt, the runs take the same interrupts a few stores apart,
       because translated code checks for them at function entries and backward branches and the
       interpreter after returns and backward branches. Every store outside the handlers is the same
       there. Frame 173's extra interrupt in the translated run comes from the same cause: the
       interpreter doesn't check at a function's entry, so it takes three pending causes in one
       interrupt where the translated run takes two.
     - The only other difference is when the timer is read: translated code adds a block's cycles
       after the block, so 750 of 57,308 timer reads come back one tick apart, changing 25 stored
       values and no store count.
