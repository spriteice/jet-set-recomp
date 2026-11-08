# Upstream

Jet Set Recomp is built on [dream-recomp](https://github.com/phobos665/dream-recomp) by phobos665.

- **`spriteice/dream-recomp`** is our copy. Its `main` started at `51ca2766d2eb` (2026-10-29), with
  libchdr at `8e7b8bd`. Our translator and runtime fixes go on that `main`.
- **`data/dream-recomp.pin`** names the commit this repo builds on, and
  `scripts/01_fetch_dream_recomp.sh` fetches it into `third_party/dream-recomp`. It's never vendored.
- **Moving the pin** is its own commit: re-emit, rebuild, rerun the regression gate and every
  10-minute run in `data/baseline.json`, the card runs included, and record the new pin in
  `data/baseline.json` (`built_from` and `reproduced_on`). A change to any count or speed in it needs
  the maintainer's approval.
- **Pulling upstream's progress in.** phobos665's `main` keeps moving (its `docs/progress.md` ledger has
  the renderer, discovery and GD-ROM work packages in progress), and every port built on a tool updates
  it. At each phase exit (`docs/status.md`, "What's open"), read upstream's `main` since the last merge;
  merge it into `spriteice/dream-recomp`'s `main` (merge, never rebase: our `main` is public and carries
  our signed commits); fix what the merge breaks there with tests, as for any change; then move the pin
  here as its own commit with the full gate and every baseline run, as for any pin move. The merge
  commit's message says what came in, and the divergence list below is brought up to date. Read
  upstream's state from its ledger and code, not its README, which has been ahead of the ledger (the
  maintainer, 6 November 2026).
- **Last read 8 November 2026,** at phase 1's exit: upstream's `main` is still `51ca276` (29 October), our
  base, so there was nothing to merge. Two of its other branches hold work its `main` doesn't, from
  mid-September: `fix/flash-region-and-erase` (save states at stage 1, capturing a call's inputs and
  running it offline, a log of every run) and `spike/flycast-redux-oracle` (an AICA key-on fix, in code
  upstream's `main` has changed since, and two reference titles). This rule covers `main`; taking work
  from either branch is a proposal of its own (the shared folder's `reviews/upstream-check-2026-11-08.md`).
- **Divergence,** our commits that upstream doesn't have, 28 on 8 November 2026 (`51ca276..71d5a66`): the
  four that set up the pin `6c098df` (the headless build, the resumed entry poll, the FMA guard,
  `vulkan-1.def`), `697bfc8` (each block's exit written once), `cdd66be` (dcdisc across drives), the
  seven of 6 November 2026 for `known-bugs.md` 11, 12, 15, 17, 18 and 19 (`6c6cc9f`, `8e409b0`, `ab1faa7`,
  `ef7c0a6`, `73018dc`, `795dcb8`, `b222a6a`), the gate's replay scenario (`98bb9fa`), the window and its
  pacing for 22, 23, 25, 26, 34 and 35 (`8df9635`, `86e2b2a`, `c1016c5`, `da5830c`, `b76cc75`, `d990818`),
  three CI fixes for 28 and 29 (`a205ea9`, `45bbffe`, `782469f`), the floating-point modes for 37 and 36
  (`56a4277`, `3023c32`), resume labels for 39 (`0204111`), the dev interpreter's `--exec-coverage`
  (`f8671ad`), and the texture cache dropping what the game writes over for 41 (`71d5a66`, the pin in
  `data/dream-recomp.pin`).
- **Offering anything to phobos665/dream-recomp is publishing,** and waits for the maintainer. Every
  commit in the divergence list fixes or extends dream-recomp itself. The maintainer chose "Not yet" on
  5 November 2026, so they stay on our copy until the maintainer decides.
- **dream-recomp's conventions:** our commits there follow its `CONTRIBUTING.md` where it applies to us:
  clang-format 20.1.7, a differential test for every emitter change, and an ADR in its `docs/decisions/`
  for a decision that changes a model (the maintainer, 5 November 2026). Its `WP x.y` commit references
  are skipped: our work isn't in its work-package plan, and a number made up for it would mislead. The
  block-exit fix (`697bfc8`) came before this rule and recorded its model change in
  `docs/emitter-design.md` there.
- **Credit:** [CREDITS.md](../CREDITS.md). Docs describe dream-recomp's work respectfully, never as
  criticism.
- **Alternatives looked at:** [research-dreamcomp.md](research-dreamcomp.md).
