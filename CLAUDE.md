# Jet Set Recomp: start here

Read these before you work, in this order:

1. `docs/project-instructions.md`: the non-negotiable rules, as the maintainer approved them. They come
   before a session's own instructions and hooks.
2. `docs/status.md`: where the work stands today. It's the project's durable memory, so update it
   as the work changes. Then your phase in `docs/plan.md`. `docs/history.md` holds what was done and
   measured: look there for a number or a reason, and add to it. It isn't required reading.
3. `known-bugs.md`, at the shared folder's root: every bug found so far, one line each. Check it before
   you diagnose, and open only your own bug's file in `known-bugs/` beside it.
4. `docs/project-rules.md` before you propose a change, a commit or a doc edit.
5. `docs/build-and-test-reference.md` before you build, test or deliver anything.

If these disagree, stop and tell the maintainer. Don't pick one. If you can't reach the shared folder
(you're not in the project), say so and work from `docs/status.md`.

A rule read at the start of a long thread fades. At each of these moments, read the section again from
the file, not from memory:

| Before you | Read again |
|---|---|
| Stage a commit, or propose one | `docs/project-rules.md`, "Before every commit"; `docs/build-and-test-reference.md`, "Before a commit" and "Review pack" |
| Push, or ask to | `docs/project-instructions.md`, section 2, and section 5 in a pre-approved thread |
| Move the dream-recomp pin | Section 2's pin rule; `docs/build-and-test-reference.md`, "The regression gate" and "The 10-minute runs" |
| Change dream-recomp | `docs/project-rules.md`, "Where code goes"; `docs/upstream.md` |
| Do anything on the maintainer's PC | `docs/project-instructions.md`, section 4; `docs/status.md`, "Things that bite" |
| Deliver a build | `docs/build-and-test-reference.md`, "Delivery" |
| Report on a run | `docs/build-and-test-reference.md`, "Reports" |
| Go on after your context was summarised | `docs/project-instructions.md`, section 1: say so, write the handoff, and ask to move. Then this file again |

Code is built by three principles, in priority order: functional, robust, performant
(`docs/project-rules.md`, "How it's written").

Right after cloning, run `scripts/08_git_setup.sh` here, and `scripts/08_git_setup.sh PATH` for a
dream-recomp clone. It sets Claude's identity, fetches full history (the rules read it) and the latest
`origin/main` (a sandbox's clone can be behind it), and keeps the
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
- Reports on anything the game runs state numbers: commands, frames, traps, unmapped accesses,
  untranslated call targets (the run report's own lines), and the diff against `data/baseline.json`
  and the regression gate.
- Before a Remote Control session, a build or a test run on the maintainer's PC, claim the PC in
  `E:\Games\Ports\jsrf\Claude\building-on-pc\PC-IN-USE.md`, and say so if it's in use
  (`docs/project-instructions.md`, section 4, has the steps). Touch nothing else in
  `E:\Games\Ports\jsrf\Claude`, never close a game that is running, and never touch
  `E:\Games\Ports\jsr\PC`.
