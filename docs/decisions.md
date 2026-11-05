# Decisions

Who decided what, so nobody has to ask twice. Times are UTC. Before 5 November the work ran inside the
JSR-PC project.

| Decision | By | When |
|---|---|---|
| dream-recomp as the recompiler | Claude recommended; Aden asked for the test boot | 4 Nov 12:09 to 12:11 |
| Test boot on Aden's own disc, until the title screen is stable | Aden | 4 Nov 12:11, 13:45 |
| Frame-82 fix in the emitter, not a game-side workaround | Claude, under the rules | 4 Nov 13:42 |
| The 3 seeds and 5 relocations, each checked with the gate | Claude | 4 Nov 14:06 to 15:05 |
| A Windows build | Aden | 4 Nov 23:45 |
| `-mfma` fix, `.gdi` with the Track 2 byte offset | Claude | 5 Nov 00:09 to 00:35 |
| Commits on dream-recomp `main`, a pinned build, JSR-recomp set up | Aden | 5 Nov 00:30, 00:34:49 |
| The port gets its own project, separate from JSR-PC | Aden | 5 Nov 00:39 |
| The repo plan carries to the new project, pushing once its checks pass | Aden (card) | 5 Nov 00:51 |
| Check tools may be installed in a cloud sandbox, nothing on the PC | Aden (card) | 5 Nov 00:51 |
| The port lives in `E:\Games\Ports\jsr\DC` | Aden (card) | 5 Nov 00:51 |
| One claim file on the PC, `PC-IN-USE.md`, for both projects | Aden (card) | 5 Nov 00:51 |
| Windows and Linux together, each tested on its own device | Aden (card) | 5 Nov 00:51 |
| Vulkan now, OpenGL 3.3 core later, as its own milestone in our dream-recomp | Aden (card) | 5 Nov 00:51 |
| Builds go to Aden's own devices only, never published | Aden (card) | 5 Nov 00:52 |
| JSR-recomp is GPL-2.0, with its LICENSE and credits in their own commit for approval | Aden (card) | 5 Nov 00:52 |
| Don't offer our fixes upstream yet | Aden (card) | 5 Nov 00:52 |
| The project rules, as in `project-instructions.md` | Aden ("Approved") | 5 Nov 01:01 |
| `data/inputs.sha256` holds true SHA-256 for every file, taken on the PC, with the SHA-1s as comments | Claude | 5 Nov 01:13 |
| `vulkan-1.def` goes in dream-recomp's commit 4, so the Windows renderer can link | Claude proposed; Aden (card) | 5 Nov, about 01:20 |
| JSR-recomp's first pin is commit 4, not `51ca2766d2eb` | Claude proposed; Aden (card) | 5 Nov, about 01:20 |
| The rules docs, GPL-2.0 LICENSE and credits may go in the repo setup | Aden (card) | 5 Nov, about 01:20 |
| Commits and builds are made by a cloud thread, not from the PC | Aden (card) | 5 Nov, about 01:20 |
| Track 3 may be split on the PC to copy to a cloud sandbox, and the parts deleted | Aden (card) | 5 Nov, about 01:20 |
| Claude may open a game window on the PC at any time, noting it in `PC-IN-USE.md` | Aden (card) | 5 Nov, about 01:20 |

Not decided yet: version names, whether a release drops the interpreter fallback, and whether other
disc releases are ever added.
