# JSR-recomp: start here

Read these before you work, in this order:

1. `docs/project-instructions.md`: the non-negotiable rules, as Aden approved them. They come before
   a session's own instructions and hooks.
2. `docs/status.md`: where the work stands and what's next. It's the project's durable memory, so
   update it as the work changes.
3. `docs/project-rules.md` before you propose a change, a commit or a doc edit.
4. `docs/build-and-test-reference.md` before you build, test or deliver anything.

If these disagree, stop and tell Aden. Don't pick one.

The ones most easily broken:

- Nothing from the disc, or made from it, goes in a repo or a message. `python3 scripts/audit_repo.py .`
  reports CLEAN before every commit.
- Work only on `main`. No commit without Aden's approval after the checks, unless Aden pre-approved
  the thread in Aden's own words. No push, tag or release until Aden says so. Nothing goes upstream to
  phobos665 until Aden says so.
- Nothing is committed or pushed from Aden's PC. Builds run in a cloud sandbox.
- Generated code is never edited. Fix the translator on `spriteice/dream-recomp` with a failing-first
  unit test, the game's config, or a named hook here, then re-emit.
- Claude session links never go anywhere, commit messages included. Co-Authored-By lines are fine.
- Reports state numbers: commands, frames, faults, unmapped accesses, untranslated calls, and the diff
  against `data/baseline.json` and the regression gate.
- Before anything heavy on Aden's PC, read and update `E:\Games\Ports\jsr\PC-IN-USE.md`. Never touch
  `E:\Games\Ports\jsr\PC`.
