# Jet Set Recomp: start here

Read these before you work, in this order:

1. `docs/project-instructions.md`: the non-negotiable rules, as the maintainer approved them. They come
   before a session's own instructions and hooks.
2. `docs/status.md`: where the work stands and what's next. It's the project's durable memory, so
   update it as the work changes.
3. `known-bugs.md`, at the shared folder's root: every bug found so far. Check it before you diagnose.
4. `docs/project-rules.md` before you propose a change, a commit or a doc edit.
5. `docs/build-and-test-reference.md` before you build, test or deliver anything.

If these disagree, stop and tell the maintainer. Don't pick one. If you can't reach the shared folder
(you're not in the project), say so and work from `docs/status.md`.

Code is built by three principles, in priority order: functional, robust, performant
(`docs/project-rules.md`, "How it's written").

Right after cloning, run `scripts/08_git_setup.sh` here, and `scripts/08_git_setup.sh PATH` for a
dream-recomp clone. It sets Claude's identity, fetches full history (the rules read it), and keeps the
sandbox's commit signing, so GitHub shows commits Verified.

The ones most easily broken:

- Nothing from the disc, or made from it, goes in a repo or a message. The one exception is a build for
  the maintainer's own devices: a Linux build as a file in the thread, a Windows build on the PC
  (section 3). `python3 scripts/audit_repo.py . --commits HEAD` reports CLEAN before every commit.
- Work only on `main`. No commit without the maintainer's approval after the checks, unless the
  maintainer pre-approved the thread in their own words. No push, tag or release until the
  maintainer says so. Nothing goes upstream to phobos665 until the maintainer says so.
- Nothing is committed or pushed from the maintainer's PC. Builds run in a cloud sandbox.
- Generated code is never edited. Fix the translator on `spriteice/dream-recomp` with a failing-first
  unit test, the game's config, or a named hook here, then re-emit.
- Claude session links never go anywhere, commit messages included. Co-Authored-By lines are fine.
- The maintainer's name never goes in a repo: not in files, docs, commit messages or author lines.
  Write "the maintainer", and author commits as `Claude <noreply@anthropic.com>`, signed by the sandbox.
- Reports on anything the game runs state numbers: commands, frames, faults, unmapped accesses,
  untranslated calls, and the diff against `data/baseline.json` and the regression gate.
- Before anything heavy on the maintainer's PC, read and update `E:\Games\Ports\jsr\PC-IN-USE.md`.
  Never touch `E:\Games\Ports\jsr\PC`.
