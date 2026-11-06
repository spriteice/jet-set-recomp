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
- **Divergence,** our commits that upstream doesn't have: the four that set up the pin `6c098df`
  (the headless build, the resumed entry poll, the FMA guard, `vulkan-1.def`), `697bfc8` (each block's
  exit written once), `cdd66be` (dcdisc across drives), and the seven of 6 November 2026 for
  `known-bugs.md` 11, 12, 15, 17, 18 and 19 (`6c6cc9f`, `8e409b0`, `ab1faa7`, `ef7c0a6`, `73018dc`,
  `795dcb8`, `b222a6a`, the last of them being the pin in `data/dream-recomp.pin`).
- **Offering anything to phobos665/dream-recomp is publishing,** and waits for the maintainer. Every
  commit in the divergence list fixes dream-recomp itself. The maintainer chose "Not yet" on
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
