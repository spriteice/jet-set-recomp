# Project rules

How a change to Jet Set Recomp is placed, written, checked and proposed. It's written by the maintainer
("I") for whoever makes the change ("you"), and goes with `docs/project-instructions.md`, the short
rules, which win over this file only by stopping the work: if they disagree, stop and tell me.
`docs/build-and-test-reference.md` covers building, testing and reports. Adapted from the JSRF-PC
rules pack of 4 November 2026.

## Before every commit

Do all six, in one review pack (`docs/build-and-test-reference.md`, "Review pack"), then wait for my
approval. A pre-approved thread doesn't wait (`docs/project-instructions.md`, section 5).

1. Run `git status`, `git diff --cached --stat` and `python3 scripts/audit_repo.py . --commits HEAD`, and
   confirm that nothing on the "never in the repo" list is staged. If `.gitignore` doesn't cover it, tell me.
2. Show me the full diff.
3. Show me the proposed commit message.
4. For a fix: the root cause and the model behind it, and its regression test. For a feature: where
   it lives, and why that's the right place.
5. For any added or edited document: the whole document, not only its diff.
6. The checks for the commit's exact tree (`docs/build-and-test-reference.md`, "Before a commit").

## Where code goes

Decide this first.

1. **The root cause, not the symptom.** A root cause has two parts: what went wrong, and the model that
   let it happen. Name both, and say whether the same model allows other bugs. If the model is the
   cause, fix the model, however big that is: say so, and size it. If the right place isn't clear,
   stop and ask.
2. **The right place.** Code goes in the layer that owns the behaviour:
   - dream-recomp's translator, for how SH-4 code is translated;
   - dream-recomp's runtime, for what the console's hardware and BIOS do;
   - dream-recomp's renderer and audio, for drawing and sound;
   - `games/jgr/jgr.toml`, for what discovery missed (seeds and relocations from `--suggest-config`);
   - a named hook in this repo, for the game's own logic.

   Never make up in one layer for a bug in another.
3. **Never edit generated files.** Fix the source, then re-emit.
4. **dream-recomp's code is ours to change,** on `spriteice/dream-recomp`'s `main`, with its credit kept
   and its pin moved in a commit of its own (`docs/upstream.md`).
5. **Config entries are measured.** Each seed or relocation comes from a run, says in a comment what it
   is and how it was found, and is checked with the regression gate. A mid-function address the
   runtime resolves itself isn't seeded.
6. **Settings.** A new feature can have a setting to turn it off. A fix gets a switch back to the old
   behaviour only while it's being tested, and it's removed by the next release. Defaults are what
   ships.
7. **Hooks.** Replacing or hooking one game function is right only when that function's own logic is
   the root cause. Each is deliberate, named for what it does, and uses named constants. Its comment
   says what's wrong in the game's function, and why the translator and runtime aren't the cause. If
   many functions misbehave for one reason, fix the translator or runtime instead.
8. **A second fix in one place is a review.** Before proposing a fix, read the code's history
   (`git log -L`). If it already had a fix for a related bug, propose a review of the mechanism first.

## How it's written

In priority order:

1. **Robust:** handle the general case. Model what the console does, not what one case needs.
2. **Focused:** one change per commit. A commit either restructures, with no change in behaviour, or
   changes behaviour, never both.
3. **Clean:** match the surrounding style. dream-recomp's C++ passes clang-format 20.1.7.

Reuse what exists: search before adding a function, and justify each new one.

**Every fixed bug gets a regression test** that fails without the fix and passes with it. Every change
to dream-recomp's emitter also follows its own rule on differential tests (its `CONTRIBUTING.md`). If
a bug can't be reached from a test without the game, say why, and add what would catch it again: an
always-on check that counts in the run log, or a step on the test list. Not a bare `assert`: every
build is `Release`, which compiles asserts out.

**Tests link the code they test,** never a copy or a piece cut out of a file.

**Docs change with the code,** in the same commit. `docs/status.md`, `known-bugs.md` and the backlog
are kept current as the work happens.

## Never do

Stop and tell me why instead.

- Per-address special cases that hide a symptom. A measured config entry or a named hook isn't one.
- Bare numbers: magic numbers, and unnamed addresses or offsets, in code.
- Sleeps or retries that hide timing bugs.
- Failing silently. Every exit says why on screen, a launcher stops before the program when a file it
  needs is missing, and the program writes its run log on every exit path it can.
- Making up in one layer for a bug in another.

## Workflow

1. **Diagnose:** reproduce from my run logs or a run of yours, gather evidence, and read the code's
   history. Write down what was seen, the root cause, the evidence, your confidence, and what would
   prove it wrong. For a behaviour difference, `--write-hash` and `--write-log` find the first
   divergence; start there rather than at the symptom.
2. **Propose** the fix at the root, sized to the cause, and wait for my go-ahead before editing. A test
   build can carry a fix before that, to test the diagnosis. A pre-approved thread posts the diagnosis
   and goes on.
3. **Implement,** with the regression test and the docs.
4. **Verify** what you can, and call everything else "unverified". Never claim something is fixed
   without evidence. A change made for speed is measured before and after.
5. **Track my testing.** Read every run log I send in full, and check it against the test list.
   A step is tested only when my results show it. Before asking me to approve a commit, list the
   untested steps and the device each needs.
6. **Report** with numbers (`docs/build-and-test-reference.md`, "Reports").

Several items can run at once, each in its own thread, if they don't change the same code. Commits
still go onto `main` one at a time, each from the latest `origin/main`. Fetch just before pushing. If
`origin/main` moved, rebase and rerun the repo checks; rerun the builds and the gate too if the commits
in between touched code, config or the pin.

If a rule conflicts with the task, or you can't solve it within the rules, stop and ask. Don't quietly
bend the rule.

## What a pre-approval still stops for

`docs/project-instructions.md`, section 5 is the rule. It also stops for: a check or step that still
fails after two fixes, a failure it can't explain or didn't cause, anything newly installed beyond
section 4's list, a second fix in one place, and whether a bug is critical. Other bugs it finds go in
`known-bugs.md` and are told to me, and aren't fixed in that thread.

## Platforms

Windows and Linux only, on x86-64 hosts, built together from the same code, each tested on its own
device. Linux must run on SteamOS, including Game Mode under gamescope, so don't assume a desktop
window manager, mouse or keyboard. For every change, say which platforms you built or verified, and
which you couldn't.

## Documents

The README, the docs it links, the changelog and release notes are human readable first, simple and
concise while holding everything relevant, and in one format. They credit dream-recomp and phobos665,
stay respectful of it, and say "bring your own disc".
