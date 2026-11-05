# Upstream

Jet Set Recomp is built on [dream-recomp](https://github.com/phobos665/dream-recomp) by phobos665.

- **`spriteice/dream-recomp`** is our copy. Its `main` started at `51ca2766d2eb` (2026-10-29), with
  libchdr at `8e7b8bd`. Our translator and runtime fixes go on that `main`.
- **`data/dream-recomp.pin`** names the commit this repo builds on, and
  `scripts/01_fetch_dream_recomp.sh` fetches it into `third_party/dream-recomp`. It's never vendored.
- **Moving the pin** is its own commit: re-emit, rebuild, rerun the regression gate and the two
  10-minute runs, and record the new pin in `data/baseline.json` (`built_from` and `reproduced_on`). A
  change to any count or speed in it needs the maintainer's approval.
- **Offering anything to phobos665/dream-recomp is publishing,** and waits for the maintainer. Two of our
  changes fix dream-recomp itself: the headless build, and the resumed entry poll. The maintainer chose "Not
  yet" on 5 November 2026, so they stay on our copy until the maintainer decides.
- **Credit:** [CREDITS.md](../CREDITS.md). Docs describe dream-recomp's work respectfully, never as
  criticism.
- **Alternatives looked at:** [research-dreamcomp.md](research-dreamcomp.md).
