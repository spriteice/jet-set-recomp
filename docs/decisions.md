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
| Code is built by three principles, in priority order: functional, robust, performant | Maintainer | 5 Nov 10:27 to 10:32 |
| Commits are signed with a signing-only SSH key from the cloud environment, so GitHub shows them Verified | Claude proposed; Maintainer (card) | 5 Nov 10:39 |
| A pre-approved thread may move the pin to its own dream-recomp work when nothing measured changes | Claude proposed; Maintainer (card) | 5 Nov 10:39 |
| The 10-minute runs' sandbox speed is a stand-in for performance, with a 15% margin | Claude proposed; Maintainer (card) | 5 Nov 10:39 |
| A recorded 5-minute play-through joins the gate, and each drawing feature fixed gets its own unit test | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| A release drops the interpreter fallback only once play logs show 0 untranslated calls | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| Shadows are drawn next, before other bugs | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| The Game Mode error dialog is checked as a step in the next Linux build | Claude proposed; Maintainer (card) | 5 Nov 11:11 |
| Commits are authored as `Claude <noreply@anthropic.com>`, signed by the sandbox, so GitHub shows them Verified; this replaces the signing key of 10:39 | Maintainer | 5 Nov 11:22 |
| Both repos' history is re-made as Claude, signed: every commit of this repo, and our four on dream-recomp, not phobos665's; old hashes are mapped in `docs/commit-map.md` | Claude proposed; Maintainer (card) | 5 Nov 11:26 |

Not decided yet: version names, and whether other disc releases are ever added.
