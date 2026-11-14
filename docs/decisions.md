# Decisions

Who decided what, so nobody has to ask twice. Times are UTC. Before 5 November the work ran inside the
JSR-PC project.

| Decision | By | When |
|---|---|---|
| dream-recomp as the recompiler | Claude recommended; the maintainer asked for the test boot | 4 Nov 12:09 to 12:11 |
| Test boot on the maintainer's own disc, until the title screen is stable | Maintainer | 4 Nov 12:11, 13:45 |
| Frame-82 fix in the emitter, not a game-side workaround | Claude, under the rules | 4 Nov 13:42 |
| The 3 seeds and 5 relocations, each checked with the gate | Claude | 4 Nov 14:06 to 15:05 |
| A Windows build | Maintainer | 4 Nov 23:45 |
| `-mfma` fix, `.gdi` with the Track 2 byte offset | Claude | 5 Nov 00:09 to 00:35 |
| Commits on dream-recomp `main`, a pinned build, JSR-recomp set up | Maintainer | 5 Nov 00:30, 00:34:49 |
| The port gets its own project, separate from JSR-PC | Maintainer | 5 Nov 00:39 |
| The repo plan carries to the new project, pushing once its checks pass | Maintainer (card) | 5 Nov 00:51 |
| Check tools may be installed in a cloud sandbox, nothing on the PC | Maintainer (card) | 5 Nov 00:51 |
| The port lives in `E:\Games\Ports\jsr\DC` | Maintainer (card) | 5 Nov 00:51 |
| One claim file on the PC, `PC-IN-USE.md`, for both projects | Maintainer (card) | 5 Nov 00:51 |
| Windows and Linux together, each tested on its own device | Maintainer (card) | 5 Nov 00:51 |
| Vulkan now, OpenGL 3.3 core later, as its own milestone in our dream-recomp | Maintainer (card) | 5 Nov 00:51 |
| Builds go to the maintainer's own devices only, never published | Maintainer (card) | 5 Nov 00:52 |
| JSR-recomp is GPL-2.0, with its LICENSE and credits in their own commit for approval | Maintainer (card) | 5 Nov 00:52 |
| Don't offer our fixes upstream yet | Maintainer (card) | 5 Nov 00:52 |
| The project rules, as in `project-instructions.md` | Maintainer ("Approved") | 5 Nov 01:01 |
| `data/inputs.sha256` holds true SHA-256 for every file, taken on the PC, with the SHA-1s as comments | Claude | 5 Nov 01:13 |
| `vulkan-1.def` goes in dream-recomp's commit 4, so the Windows renderer can link | Claude proposed; Maintainer (card) | 5 Nov, about 01:20 |
| JSR-recomp's first pin is commit 4, not `51ca2766d2eb` | Claude proposed; Maintainer (card) | 5 Nov, about 01:20 |
| The rules docs, GPL-2.0 LICENSE and credits may go in the repo setup | Maintainer (card) | 5 Nov, about 01:20 |
| Commits and builds are made by a cloud thread, not from the PC | Maintainer (card) | 5 Nov, about 01:20 |
| Track 3 may be split on the PC to copy to a cloud sandbox, and the parts deleted | Maintainer (card) | 5 Nov, about 01:20 |
| Claude may open a game window on the PC at any time, noting it in `PC-IN-USE.md` | Maintainer (card) | 5 Nov, about 01:20 |
| The repo is renamed `spriteice/jet-set-recomp`, shown as "Jet Set Recomp"; older rows keep the old name, JSR-recomp | Maintainer (card) | 5 Nov 09:57 |
| Gate captures and write hashes are kept between sandboxes in the shared folder's `captures/` | Claude proposed; Maintainer (card) | 5 Nov 10:03 |
| Every choice, approval or decision for the maintainer goes on a card, never only in plain text | Maintainer | 5 Nov 10:22 |
| Code is built by three principles, in priority order: functional, robust, performant | Maintainer | 5 Nov 10:27 to 10:32 |
| Commits are signed with a signing-only SSH key from the cloud environment, so GitHub shows them Verified | Claude proposed; Maintainer (card) | 5 Nov 10:39 |
| A pre-approved thread may move the pin to its own dream-recomp work when nothing measured changes | Claude proposed; Maintainer (card) | 5 Nov 10:39 |
| The 10-minute runs' sandbox speed is a stand-in for performance, with a 15% margin | Claude proposed; Maintainer (card) | 5 Nov 10:39 |
| A recorded 5-minute play-through joins the gate, and each drawing feature fixed gets its own unit test | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| A release drops the interpreter fallback only once play logs show 0 untranslated calls | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| Shadows are drawn next, before other bugs | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| The Game Mode error dialog is checked as a step in the next Linux build | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| Commits are authored as `Claude <noreply@anthropic.com>`, signed by the sandbox, so GitHub shows them Verified; this replaces the signing key of 10:39 | Maintainer | 5 Nov 11:22 |
| If Ubuntu's snapshot server is ever needed, its packages are pushed to our GitHub first, and every local build, sandbox and GitHub CI installs only from there; the server is used only to update the copy | Maintainer | 5 Nov 11:55 to 11:56 |
| Every test build has the files it needs to play out of the box: setup already run for the maintainer's disc before it's handed over. For the Ally X, amended at 13:34: the maintainer copies the disc in with `copy-disc.sh` | Maintainer | 5 Nov 12:13 |
| A ready-to-play Ally X build is made on the PC, where the disc is, with the disc's tracks inside, and the maintainer copies it to the Ally X | Claude proposed; Maintainer (card) | 5 Nov 12:23 |
| The save bundled in a test build is the one furthest through the game, not the newest | Maintainer | 5 Nov 12:24 |
| A full coverage pass ("map everything first") comes before any renderer work, and the renderer threads pause | Maintainer (card) | 5 Nov 12:36 |
| Our dream-recomp commits write an ADR in its `docs/decisions/` for a decision that changes a model, and skip its `WP x.y` references | Claude proposed; Maintainer (card) | 5 Nov 12:43 |
| The two `--vmu` baseline runs are made on the PC's Windows build; their Linux sandbox speed is recorded at the next pin move | Claude proposed; Maintainer (card) | 5 Nov 12:43 |
| The work runs in six phases, in order: map the code; tell translation faults from renderer faults; runtime and platforms; the renderer, one hardware feature at a time, depth before shadows; the whole game; then speed, OpenGL and release. Recorded play-throughs move into the first phase. This replaces "shadows next" of 11:11 | Claude proposed; Maintainer (card) | 5 Nov 12:49 |
| The Ally X build carries everything but the game files, which are too large: it's delivered with the save, the maintainer copies the game files to the Ally X themselves, and the package supplies a script that puts them in place. This replaces the PC-made archive of 12:23 | Maintainer | 5 Nov 13:34 |
| The second pass's five refinements to phases 2 to 5 (`reviews/recomp-work-order-second-pass-2026-11-06.md`, shared folder): phase 2 names what its oracle can't see; pacing is measured on both devices in phase 3 and re-measured in phase 5; phase 4 needs a reference frame per bug from the disc on Flycast or a Dreamcast, uses KOS `pvr` examples as test scenes, and names each device's renderer path; phase 5 starts with an acceptance matrix and ends with the release configuration passing it | Claude proposed; Maintainer (card) | 6 Nov 01:28 |
| The first SteamOS smoke test runs now: the pin-move build goes to both devices, a Linux package with `copy-disc.sh` for the Ally X alongside the Windows build | Claude proposed; Maintainer (card) | 6 Nov 01:28 |
| Upstream dream-recomp is merged into our `main` at each phase exit, as a pin move with the full gate and baseline (`docs/upstream.md`), and `scripts/08_git_setup.sh` installs the audit as commit hooks | Claude proposed; Maintainer (card) | 6 Nov 01:28 |
| Phase 6 adds a Windows-hosted build path (MSVC or clang-cl) and a timed clean-checkout build on both OSes by someone who isn't us | Claude proposed; Maintainer (card) | 6 Nov 01:28 |
| The long-term goal includes the EU and Japanese Dreamcast releases, then HD textures from the PC version, with toggles so the player picks content from each (songs, localisation, HD textures). The discs are Jet Grind Radio (USA), Jet Set Radio (Europe) and De La Jet Set Radio (Japan) | Maintainer | 6 Nov 06:27, 06:39 |
| Groundwork for the other releases now, and their discs mapped from phase 5's start (`reviews/multi-region-plan-2026-11-06.md`, shared folder). Meanwhile nothing new is designed USA-only: the first hook names its release by the boot file's hash, and the texture cache keys textures by their data's hash | Claude proposed; Maintainer (card) | 6 Nov 06:36 |
| The PC's one claim file is `E:\Games\Ports\jsrf\Claude\building-on-pc\PC-IN-USE.md`, for every project that uses the PC; `E:\Games\Ports\jsr\PC-IN-USE.md` is no longer used. This replaces the claim file of 5 Nov 00:51 | Maintainer | 6 Nov 06:49 |
| Threads work on the PC through folder access for files (reading, copying, writing the claim) and through Remote Control for running anything; this widens "only through Remote Control" in the rules | Claude proposed; Maintainer (card) | 6 Nov 06:59 |
| The maintainer's recording 1 of 8 Nov (the Garage tutorial, mission 1 and Kogane, on a new card) replaces the 5 Nov recording, stale since pin `3023c32`, in `data/baseline.json` and as the gate's replay scenario. Recording 2 (Shibuya-cho) starts from the maintainer's save, which never goes in a repo, so it stays in the shared folder and is replayed by hand from the save | Claude proposed; Maintainer (cards) | 8 Nov 09:21, 09:22 |
| Phase 1 has exited, on every exit line's numbers (shared folder `reviews/next-after-phase-1-2026-11-08.md`). Recording 1, which plays the tutorial and the first stage, meets the recordings item alone. Bugs 24 and 40 stay open outside the exit: nothing in this game reaches 24, and 40 shows only on the stale 5 November recording, its question being phase 2's. The phase-exit upstream check comes before phase 2 | Claude proposed; Maintainer (card) | 8 Nov 13:21 |
| Phase 2 starts with a per-bug check, with no new code: recording 1 runs translated and interpreted (`--interpret`) to the spots of bugs 5, 7 and 9, on one build and one renderer in a sandbox with the disc, and a bug that shows in both isn't the translator's. Bigger tools, upstream's save states or the dev interpreter taking interrupts where translated code does, each come on their own card, and only if a bug can't be placed this way | Claude proposed; Maintainer (card) | 8 Nov 14:42 |
| Jet Set Recomp is GPL-2.0-only, the licence dream-recomp is under, rather than GPL-2.0-or-later. LICENSE is the FSF's text byte for byte, and every file of code or configuration names the licence on an `SPDX-License-Identifier` line, which the scripts' tests check. dream-recomp keeps its own licence: it's phobos665's to set | Claude proposed; Maintainer (card) | 8 Nov 16:44 |
| Bug 9, skate sparks that stay where they spawned, is the game's own behaviour, and the bug is closed | Maintainer | 14 Nov 00:44 |
| Phase 2 has exited, on both exit lines (shared folder `reviews/phase-2-exit-2026-11-14.md`). Bugs 5 and 7 are the renderer's, with their causes; 9 is the game's own behaviour and closed; 8 is gone since bug 41's fix. Every write-hash difference between recording 1's translated and interpreted runs is explained, none a translation fault, and recording 2's is taken as the same two causes. The upstream check found nothing to merge. Phase 3 is next | Claude proposed; Maintainer (card) | 14 Nov 00:49 |
| The PC claim's steps, in the maintainer's own words (`docs/project-instructions.md`, section 4): read `PC-IN-USE.md` before a Remote Control session, a build or a test run; if it's in use, wait or work in the cloud, and say so; if it's free, replace its last line with the claim (project, thread title, what runs, the expected end), and write "Free from ..." back when the session ends; touch nothing else in `E:\Games\Ports\jsrf\Claude`, and never close a game that is running. This replaces "add a line" and "before anything heavy" | Maintainer | 14 Nov 05:44, 05:47 |
| The bug list is an index with one file per bug, and `docs/status.md` is split into the state, the plan and the history. The same card landed the rules review's other two changes of that hour: six stale lines corrected, and the table in `CLAUDE.md` of what to read again, and when | Claude proposed; Maintainer (card) | 14 Nov 06:02 |
| The documents' pointers are checked by `scripts/check_docs.py`, in CI too, and `scripts/check_push.py` is the pre-push hook: it refuses a push of anything but `main`, one that isn't a fast-forward, one made while a release is under way, and one whose commits don't pass the audit | Claude proposed; Maintainer (card) | 14 Nov 06:35 |
| `scripts/30_compare_runs.py` makes the comparison of run reports with `data/baseline.json` | Claude proposed; Maintainer (card) | 14 Nov 06:50 |
| `scripts/review_pack.py` starts a review pack from the staged change, with the checks run on a copy of exactly what is staged | Claude proposed; Maintainer (card) | 14 Nov 07:05 |
| Phase 6 is planned from the code, and adds Super-xBR upscaling (textures, menus, the HUD and graffiti), draw-distance options for graffiti cans, vehicles, characters, crowds, police and police vehicles, and further widescreen work (true widescreen rendering, the HUD and the menus) | Maintainer | 14 Nov 08:30 |
| A free camera with the feel of the maintainer's JSRF-PC project is studied now: the camera study and the hook mechanism's design start beside phase 3, with no code, and building waits for phase 3's exit and the design's approval (the shared folder's `reviews/free-camera-viability-2026-11-14.md`) | Claude proposed; Maintainer (card) | 14 Nov 08:41 |
| The hook mechanism, as the shared folder's `reviews/hook-design-proposal-2026-11-14.md` describes it in sections 1 to 10: our code runs before or after one whole game function, the translator plants the call, the runtime checks a registry of hooks at start, and the hooks' code lives in this repo. Building it waits for phase 3's exit. Its section 11, tuned values and frame notes for phase 6, joins the first build (14 Nov 13:52, below) | Claude proposed; Maintainer (card) | 14 Nov 09:02 |
| Phase 6 follows the shared folder's `phase6/PLAN.md`, with the enhancements before OpenGL and the release: faster rebuilds, a study of the game with no code, hooks, upscaling, widescreen, draw distance, then OpenGL 3.3 core, the Windows-hosted build and the release. This replaces `docs/plan.md`'s "any enhancements the maintainer wants come last". Each build step still comes to the maintainer on its own card | Claude proposed; Maintainer (card) | 14 Nov 09:02 |
| Phase 6's study of the game starts now, in its own thread, beside phase 3 and the camera study, with no code | Claude proposed; Maintainer (card) | 14 Nov 09:03 |
| With the free camera on, the small tag's spray view is off: the camera view the game shows while a small graffiti, one with no quick-time event, is sprayed | Maintainer | 14 Nov 09:06 |
| `scripts/31_pin_check.py` makes a pin move's measurements in one command: the disc check, the build, the gate and every run of the baseline, compared, with the capture folder and its manifest. It landed unverified on the game, because no sandbox had the disc, so the first pin move that uses it makes the by-hand steps as well | Claude proposed; Maintainer (card) | 14 Nov 13:00 |
| Phase 6's study may use two diagnostic switches, a read watch and a set-a-word switch, in a copy of dream-recomp that stays in its sandbox and is never committed (their diff kept in the shared folder), and Mesa's software Vulkan (lavapipe) installed in its sandbox, to look at pictures | Claude proposed; Maintainer (card) | 14 Nov 13:00 |
| The free camera's hooks, as section 12 of the shared folder's `reviews/hook-design-proposal-2026-11-14.md` describes them: one hook on the game's follow camera; with it on, the small tag's view is off, the big graffiti keeps the game's view, and an L press that sprays doesn't recentre. Built after the mechanism | Claude proposed; Maintainer (card) | 14 Nov 13:52 |
| The hook mechanism's section 11, tuned values (for draw distance) and frame notes (for widescreen), joins the mechanism's first build and its ADR, so the model changes once | Claude proposed; Maintainer (card) | 14 Nov 13:52 |
| The symbols file and the decisions rows that phase 6's study and the camera study owe are committed from a new thread, because the study's thread had its context summarised | Claude proposed; Maintainer (card) | 14 Nov 15:56 |
| Police vehicles, which recording 1 doesn't reach in play, are studied from the first recording that does, phase 5's stage recordings at the latest; nothing before draw distance needs them | Claude proposed; Maintainer (card) | 14 Nov 15:56 |

Not decided yet: version names.
