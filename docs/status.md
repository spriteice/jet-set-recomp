# Status

Where the work stands today. It's the project's durable memory, so keep it current, and keep it to
what is true now: [plan.md](plan.md) has the six phases with their entries and exits, and
[history.md](history.md) has what was done and measured on the way, with its numbers. Updated 14
November 2026. Who decided what: [decisions.md](decisions.md).

When the work moves, change the line here that it makes untrue, and put what was done, with its
numbers and where its evidence is, at the top of the log in `history.md`.

## Now

- **Pin:** `6154c9a` (`data/dream-recomp.pin`), the tip of `spriteice/dream-recomp`'s `main` on
  14 November. What each of our commits there does: [upstream.md](upstream.md), "Divergence".
- **Phase:** 3 of 6, runtime and platforms ([plan.md](plan.md)). Phase 1, mapping the code, exited
  on 8 November, and phase 2, telling translation faults from renderer faults, on 14 November.
- **Beside phase 3:** phase 6's first step, its study of the game, ended on 14 November, and so did
  the camera study for a free camera. Both wrote no code. The addresses they named are
  [games/jgr/symbols.md](../games/jgr/symbols.md). The hook mechanism, with its tuned values and frame
  notes, and the free camera's hook are approved, and wait for phase 3's exit
  ([decisions.md](decisions.md)).
- **Playable:** on Windows since 5 November, and on SteamOS on the Ally X, in Desktop Mode and Game
  Mode, since 6 November: music, saving, loading, the tutorial and the first level work.
- **Numbers:** `data/baseline.json` holds what a run is compared with: four 10-minute runs and
  recording 1's play-through, each at 0 traps, 0 unmapped accesses and 0 untranslated call targets.
  Recording 1 (`data/recordings/2026-11-08-tutorial-mission1-kogane.txt`) is the gate's third
  scenario too. Recording 2 starts from the maintainer's save, which never goes in a repo, so it
  stays in the shared folder's `recordings/` and is replayed by hand.
- **Bugs:** `known-bugs.md` in the shared folder. The open drawing bugs are phase 4's, and pacing
  while the window isn't focused (10) is phase 3's.
- **Upstream:** read at each phase exit, last on 14 November, with nothing to merge
  ([upstream.md](upstream.md)).

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
  time. The claim file, `E:\Games\Ports\jsrf\Claude\building-on-pc\PC-IN-USE.md`, is in that
  project's folder, not in `E:\Games\Ports\jsr\` (confirmed by the maintainer, 6 Nov 06:49), and its
  last line says "Free from ..." or "In use from ...". How to claim the PC and clear the claim is
  `docs/project-instructions.md`, section 4, in the maintainer's words of 14 November.
