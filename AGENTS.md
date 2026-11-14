# Agents

Any coding agent working here follows [CLAUDE.md](CLAUDE.md) and the documents it lists. This file
adds the map. Code here is functional first, then robust, then performant
(`docs/project-rules.md`, "How it's written").

## The layout

| Path | What |
|---|---|
| `games/jgr/` | The game's config (`jgr.toml`, addresses only) and its CMake entry |
| `data/inputs.sha256` | The disc's hashes |
| `data/dream-recomp.pin` | The dream-recomp commit this builds on |
| `data/baseline.json` | The numbers a run is compared with |
| `scripts/` | Git setup, sandbox setup, verify, fetch, make the `.gdi`, get the boot file, build, package, audit |
| `packaging/` | What goes in a delivery folder beside the program |
| `tests/` | Tests of the scripts, with made-up data and no disc |
| `third_party/dream-recomp/` | Fetched by script, ignored by git, and read-only here |
| `docs/` | The rules, the build reference, the status, the plan, the history and the reports |

Ignored and made on the machine: `games/jgr/disc.gdi`, `games/jgr/boot/`, `build*/`.

## Where a change goes

| The problem | The place |
|---|---|
| How SH-4 code is translated | dream-recomp `translator/`, with a unit test, then a pin move |
| What the console's hardware or BIOS does | dream-recomp `runtime/` |
| Drawing, sound | dream-recomp `render/`, `audio/` |
| Frame pacing, the window, input, anything about the host OS | dream-recomp `runtime/` and its SDL layer |
| A function no discovery rule could find (reached only through a table read at run time), or a region copied elsewhere | `games/jgr/jgr.toml`, from `--suggest-config`, checked with the regression gate; never a mid-function address |
| A function discovery's own rules missed (a scan window, a dropped switch table, an origin ranking: bug 11) | dream-recomp `translator/` analysis, with a unit test, then a pin move |
| The game's own logic is the cause | A named hook here, with a comment saying why it isn't fixed at the source |
| Building, packaging, checks | `scripts/`, `packaging/` |

## Useful facts

- `third_party/dream-recomp/tools/regress/gate.py` is the regression gate. From this repo, give it
  absolute paths: `capture LABEL --build "$PWD/build" --config "$PWD/games/jgr/jgr.toml" --game jgr`.
- Runs use `--rtc-seed 1`. Without it, the console clock comes from the host and runs diverge.
- `--write-hash FILE` gives a per-frame hash of guest writes, and it's the one signal that reliably
  catches a change in game logic. It doesn't see drawing, sound or pacing.
  `docs/test-boot-2026-11-04.md` shows how to use a write log to find the first divergence.
- The game runs its logic as tasks that switch away partway through a function, which is why resume
  entries and interrupt polls matter so much here.
