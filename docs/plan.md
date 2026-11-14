# Plan

Six phases, in order, adopted by the maintainer on 5 November (`docs/decisions.md`). A phase ends only
when its exit is shown, with numbers. Work that changes no code, such as a device smoke test, can run
alongside. The reasons, from how other recompilation projects ordered their work, are in
`reviews/recomp-work-order-2026-11-05.md` in the shared folder, with the second pass of 6 November in
`reviews/recomp-work-order-second-pass-2026-11-06.md` there (the maintainer adopted its refinements,
`docs/decisions.md`), and `release-prep/roadmap.md` there puts each milestone in its phase.

This file is the plan: each phase's entry, work and exit. Where the work stands today is in
[status.md](status.md), and what the finished phases did and measured is in [history.md](history.md).
Times are UTC unless marked UTC+8.

1. **Map the code (done 8 November).** A full coverage pass, before any renderer work. It exited on
   the maintainer's card "Close it, upstream check next", with every exit line met by its numbers:
   [history.md](history.md), "Phase 1".
2. **Tell translation faults from renderer faults (done 14 November).** It exited on the maintainer's
   card "Close it, phase 3 next", with both exit lines met: bugs 5 and 7 are the renderer's, with
   their causes, 9 is the game's own behaviour and closed, and 8 is gone on the Ally X since bug 41's
   fix: [history.md](history.md), "Phase 2". One of its notes still guides phase 4:
   - What the oracle can't see: the interpreter is dream-recomp's own, built from the same decoder and
     instruction semantics as the translator (its ADR 2), so a match can't show a bug both share: a
     decoder table, an instruction's semantics, FPSCR mode handling. Those parts are what upstream's
     differential harness checks against Flycast's interpreter (its ADR 12; `docs/upstream.md`), so
     the risk is small, not zero. A match means "not the translator", not "the renderer": when a
     renderer fix in phase 4 doesn't move a bug, the next suspect is the shared CPU model, checked
     against Flycast, not a second renderer theory.
3. **Runtime and platforms.**
   - Entry: phase 1's exit, met 8 November. The first SteamOS smoke test ran ahead of it, on
     6 November ([history.md](history.md), "SteamOS runs it"), and changed no code. Whether that build's
     Game Mode step passed (start `play.sh` before setup, to see that its error dialog shows) isn't
     recorded here.
   - Work: pacing while unfocused (`known-bugs.md`, 10). SteamOS in Desktop Mode and Game Mode. Sound through a device, a controller, and a
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
     texture formats and palettes (7, 8), and per-pixel sorting of the translucent list (5). The texture cache keys each texture by a hash of its data, not its address, so a
     replacement pack can work across releases later (phase 5, "Other releases").
   - Exit: bugs 1 and 5 to 8 fixed and passed on both devices, each with a pixel count on a capture
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
   - Other releases (the maintainer, 6 Nov 06:36): the EU and Japanese Dreamcast discs join here, once
     phases 1 to 4 have fixed the shared code on the USA disc. Each first does its own phase 1 (seeds and
     relocations, recordings, gate scenarios and baseline runs: nothing of USA's carries over to another
     binary) and phase 2 check, then joins the acceptance matrix as a release column, and the exit counts
     its rows too. Content toggles (songs, localisation) follow, then HD textures from the PC version.
     The maintainer's discs are Jet Grind Radio (USA), Jet Set Radio (Europe) and De La Jet Set Radio
     (Japan), the 2001 release built from the EU one (6 Nov 06:39). Until then nothing new is designed
     USA-only: the first hook names the release its addresses belong to, by the boot file's hash, and a
     launcher refuses another release's hook table with a message that says so; the texture cache keys by
     data (phase 4). Both new discs were measured, built and run headless on 6 November, testing only,
     at pin `98bb9fa` (`regions/FINDINGS.md` in the shared folder gathers it all; the plan is
     `reviews/multi-region-plan-2026-11-06.md` there). De La's boot file is the game, and with 4
     interrupt-vector relocations, no seeds and no translator change, its four 10-minute runs gave
     35,977 frames, 0 traps, 0 unmapped and 0 untranslated. EU's boot file is a 50/60 Hz menu that loads
     the game (`JET.BIN` or `JET_PAL.BIN`) over itself, and the translated build faults 8.8 s in,
     because the runtime goes on running the menu's translations (`known-bugs.md` 31): the config,
     translator and runtime hold one program per game, so EU starts with a model change, sized and
     proposed, before its mapping. `JET.BIN` booted directly, with the same 4 relocations, gave USA's
     no-input frames and renders with 0 traps, 0 unmapped and 0 untranslated; `JET_PAL.BIN` stops
     rendering about 110 s in, translated only (33). Both discs take their language from the console's
     setting, which the runtime always reports as English, so a language setting is the one runtime
     change every other release needs, and both discs can show it working.
6. **Rebuilds, enhancements, OpenGL and release.** Its plan is `phase6/PLAN.md` in the shared
   folder, adopted by the maintainer on 14 November (09:02, card "Adopt, enhancements first"), with the
   enhancements before OpenGL and the release. In order:
   - Rebuild cost, unless phase 1 took it (it didn't: four full builds): each config change re-emits
     81 MB of C++ in one unit and takes about 15 minutes, and every hook after it re-emits.
   - A study of the game, with no code: the screen's settings and who reads them, how the HUD and the
     menus are drawn, the game's own culling, and the draw test of each class below. It started
     beside phase 3 on 14 November (card "New thread, study now", 09:03) and ended the same day: its
     answers are the shared folder's `phase6/game-study-2026-11-14.md`, and the addresses it and the
     camera study named are [games/jgr/symbols.md](../games/jgr/symbols.md). Recording 1 reaches no
     police vehicles in play, so that class is studied from the first recording that does, phase 5's
     at the latest (15:56).
   - Hooks: the mechanism the maintainer approved on 14 November (09:02), built after phase 3's exit,
     with the plan's two additions, tuned values and frame notes, in its first build (13:52). The free
     camera's hook, approved the same day (13:52), follows it.
   - Super-xBR upscaling for world textures, menus and the HUD, and graffiti, in the texture cache that
     phase 4 rebuilds.
   - Widescreen: the 3D view first, then the HUD and the menus, each screen kept 4:3 until it has been
     checked wide.
   - Draw-distance options for graffiti cans, vehicles, characters, crowds, police and police vehicles,
     each sized from the study.
   - OpenGL 3.3 core, as its own milestone.
   - The player's build and the release. A release is source only, so the build is what a player
     gets, and today it runs on Linux alone (Windows is cross-compiled). Phase 6 adds a Windows-hosted
     build (MSVC or clang-cl, as upstream's own CI builds Windows x64), documented in the README, and a
     timed build from a clean checkout on both OSes by someone who isn't us, before the release
     checklist (`docs/release-checklist.md`) runs (the maintainer, 6 Nov 01:28).

   Every enhancement is off by default, and with it off the gate and the 10-minute runs are unchanged.
   A setting that changes what the game does says so in the menu, is written into recordings, and is
   played by hand on both devices before it can be a default. The release doesn't depend on the
   enhancements, so it can be called after any of them.
