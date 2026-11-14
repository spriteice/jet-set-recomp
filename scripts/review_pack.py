#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Write a review pack for the staged change: what the maintainer needs to approve one commit.

    python3 scripts/review_pack.py PACK --message FILE [--base REV] [--dream PATH] [--shared FOLDER]

PACK is the pack's folder, in the shared folder's review-packs/. It gets:

    commit.diff               the staged change, whole (git diff --cached)
    COMMIT_MSG.txt            the proposed message, copied from FILE
    documents/                every staged document the change adds or edits, whole. Replaced on
                              every run, so PACK is a folder of the pack's own
    evidence/repo-checks.txt  the checks and what each printed
    REVIEW.md                 the six checks of docs/project-rules.md, "Before every commit", with 1,
                              2, 3, 5 and 6 filled in from the above. Written once: a REVIEW.md that
                              is there already is yours, and is left as it is

The checks are the ones docs/build-and-test-reference.md, "Before a commit" lists for this repository:
the audit on the staged files and on the commit under them, the audit of the message, the docs
check, the scripts' tests, `bash -n` and shellcheck. The tests and the shell checks run on a copy of
exactly what is staged, made new in a temporary folder, so a file that was edited or added and not
staged can neither pass a check nor fail one: the pack shows the commit's tree, not the working tree.

    --base REV      the change is the staged tree against REV, not against HEAD: for a proposal
                    that stands on another one which isn't committed yet
    --dream PATH    a dream-recomp clone with full history, passed to the docs check
    --shared FOLDER the project's shared folder, passed to the docs check

Exits 0 when every check passed, 1 when one didn't (the pack is written all the same, and says
which), and 2 when there is nothing to make a pack of, or PACK isn't a pack's folder. It commits
nothing and stages nothing. A pack is what was checked, not an approval: the commit still waits for
the maintainer's card, unless the thread was pre-approved (docs/project-instructions.md, sections 2
and 5).
"""
from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCUMENT_SUFFIXES = {".md", ".txt"}
SHELL_SCRIPTS = ("scripts/*.sh", "packaging/*.sh")
TO_WRITE = "(to write)"
# What points a git command at another repository or index. A `git commit -a` hook, or a caller that
# reads a tree into an index of its own, sets these, and the tests make repositories of their own:
# with these still set, their `git add` would write into the caller's index.
GIT_REDIRECTS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                 "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX")


class Check:
    """One command of the evidence: what was run, what it printed, and whether it passed."""

    def __init__(self, title: str, command: list[str], cwd: pathlib.Path, shown: str | None = None,
                 own_git: bool = False):
        """own_git is for a check that runs on the copy and makes repositories of its own."""
        self.title, self.shown = title, shown or " ".join(command)
        env = {name: value for name, value in os.environ.items() if not (own_git and name in GIT_REDIRECTS)}
        try:
            done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env)
            self.output, self.passed = (done.stdout + done.stderr).rstrip("\n"), done.returncode == 0
        except OSError as missing:  # the tool isn't installed: said, and never taken for a pass
            self.output, self.passed = f"could not run {command[0]}: {missing.strerror}", False

    def text(self) -> str:
        return f"== {self.title}\n$ {self.shown}\n{self.output or '(no output)'}\n-> {'passed' if self.passed else 'FAILED'}\n"


def git(*args: str, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if check and done.returncode != 0:
        raise SystemExit(f"review_pack.py: git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def skeleton(subject: str, base: str, tree: str, stat: str, documents: list[str], rows: dict[int, str]) -> str:
    listed = ", ".join(f"`documents/{name}`" for name in documents) or "No document is added or edited"
    return f"""# Jet Set Recomp: {subject}

Proposed, not committed: one commit for `main` of `spriteice/jet-set-recomp`, on {base}. The staged
tree that was checked is `{tree}`. Its diff is `commit.diff`, its message is `COMMIT_MSG.txt`, and what
each check printed is in `evidence/repo-checks.txt`.

## What it changes

{TO_WRITE}

## The checks (`docs/project-rules.md`, "Before every commit")

| # | Check | Result |
|---|---|---|
| 1 | `git status`, the staged files, the audit | {rows[1]} |
| 2 | The full diff | `commit.diff`: {stat} |
| 3 | The commit message | `COMMIT_MSG.txt`; {rows[3]} |
| 4 | A fix: the root cause, its model and its regression test. A feature: where it lives, and why there | {TO_WRITE} |
| 5 | The documents whole | {listed} |
| 6 | The checks for the tree | {rows[6]} |

## Unverified

{TO_WRITE}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pack", metavar="PACK")
    parser.add_argument("--message", metavar="FILE", required=True)
    parser.add_argument("--base", metavar="REV", default="HEAD")
    parser.add_argument("--dream", metavar="PATH")
    parser.add_argument("--shared", metavar="FOLDER")
    args = parser.parse_args(argv)
    pack, message = pathlib.Path(args.pack).resolve(), pathlib.Path(args.message)
    if not message.is_file():
        print(f"review_pack.py: no commit message at {message}", file=sys.stderr)
        return 2
    if not message.read_text(encoding="utf-8", errors="replace").strip():
        print(f"review_pack.py: {message} is empty", file=sys.stderr)
        return 2
    # A pack's documents/ is replaced on every run, so a folder that has one and isn't a pack is refused.
    if (pack / "documents").exists() and not (pack / "commit.diff").is_file():
        print(f"review_pack.py: {pack} has a documents folder and no commit.diff, so it isn't a pack this script "
              "made. It replaces a pack's documents, so give the pack a folder of its own.", file=sys.stderr)
        return 2
    base = git("rev-parse", "--verify", "--quiet", f"{args.base}^{{tree}}", check=False).strip()
    if not base:
        print(f"review_pack.py: --base {args.base} names no commit or tree here", file=sys.stderr)
        return 2
    tree = git("write-tree").strip()  # fails, and says why, while a merge conflict is staged
    if tree == base:
        print(f"review_pack.py: nothing is staged that differs from {args.base}, so there is no change to "
              "review. Stage the change first (git add).", file=sys.stderr)
        return 2

    changed = [name for name in git("diff", "--cached", "--name-only", "--diff-filter=d", "-z", args.base).split("\0") if name]
    documents = sorted(name for name in changed if pathlib.PurePosixPath(name).suffix.lower() in DOCUMENT_SUFFIXES)
    stat = git("diff", "--cached", "--shortstat", args.base).strip() or "no line changed"
    (pack / "evidence").mkdir(parents=True, exist_ok=True)
    (pack / "commit.diff").write_text(git("diff", "--cached", args.base), encoding="utf-8")
    kept_message = pack / "COMMIT_MSG.txt"
    if message.resolve() != kept_message:
        shutil.copyfile(message, kept_message)
    shutil.rmtree(pack / "documents", ignore_errors=True)  # the last run's, which this change may no longer touch
    for name in documents:
        copy = pack / "documents" / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f":{name}"], capture_output=True,
                                        check=True).stdout)

    with tempfile.TemporaryDirectory() as folder:
        staged = pathlib.Path(folder) / "staged"
        git("checkout-index", "--all", f"--prefix={staged}/")
        python = [sys.executable]
        docs_args = [*(["--dream", args.dream] if args.dream else []), *(["--shared", args.shared] if args.shared else [])]
        shell = sorted(str(path.relative_to(staged)) for pattern in SHELL_SCRIPTS for path in staged.glob(pattern))
        checks = {
            "audit": Check("The audit: the staged files, and every commit under them",
                           [*python, str(staged / "scripts/audit_repo.py"), str(ROOT), "--commits", "HEAD"], ROOT,
                           "python3 scripts/audit_repo.py . --commits HEAD"),
            "message": Check("The audit of the proposed message",
                             [*python, str(staged / "scripts/audit_repo.py"), str(ROOT), "--message", str(kept_message)],
                             ROOT, "python3 scripts/audit_repo.py . --message COMMIT_MSG.txt"),
            "docs": Check("The docs check, on the staged documents",
                          [*python, str(staged / "scripts/check_docs.py"), str(ROOT), *docs_args], ROOT,
                          " ".join(["python3 scripts/check_docs.py .", *docs_args])),
            "tests": Check("The scripts' tests, on a copy of the staged tree",
                           [*python, "-m", "unittest", "discover", "-s", "tests"], staged,
                           "python3 -m unittest discover -s tests", own_git=True),
            "syntax": Check(f"bash -n on the {len(shell)} shell scripts of the staged tree",
                            ["bash", "-c", 'for script in "$@"; do bash -n "$script" || exit 1; done', "bash", *shell], staged,
                            "for script in scripts/*.sh packaging/*.sh; do bash -n \"$script\"; done", own_git=True),
            "shellcheck": Check("shellcheck on the same scripts", ["shellcheck", *shell], staged,
                                "shellcheck scripts/*.sh packaging/*.sh", own_git=True),
        }
        version = Check("", ["shellcheck", "--version"], staged, own_git=True)
    shellcheck_version = (re.search(r"^version: (\S+)", version.output, re.M) or [None, "not installed"])[1]
    ran = re.search(r"^Ran (\d+) tests? in", checks["tests"].output, re.M)

    status = git("status", "--short").rstrip("\n")
    unstaged = [line for line in status.splitlines() if line[1:2] != " " or line.startswith("??")]
    head, origin = git("rev-parse", "HEAD").strip(), git("rev-parse", "--verify", "--quiet", "origin/main", check=False).strip()
    evidence = [
        f"Jet Set Recomp's checks on a staged change, {datetime.datetime.now(datetime.timezone.utc):%-d %b %Y, %H:%M} UTC. "
        "Nothing was committed.",
        f"The staged tree is {tree}, a change against {args.base} (tree {base}).",
        f"HEAD is {head} on {git('rev-parse', '--abbrev-ref', 'HEAD').strip()}; origin/main is {origin or 'not known here'}.",
        "",
        "== git status --short",
        status or "(clean)",
        f"-> {len(unstaged)} line(s) are of files edited or added and not staged. The tests and the shell checks below "
        "ran on a copy of the staged tree, so those files took no part." if unstaged else "-> everything changed is staged",
        "",
        f"== git diff --cached --stat {args.base}",
        git("diff", "--cached", "--stat", args.base).rstrip("\n"),
        "",
        *(check.text() for check in checks.values()),
    ]
    (pack / "evidence/repo-checks.txt").write_text("\n".join(evidence), encoding="utf-8")

    failed = [name for name, check in checks.items() if not check.passed]

    def result(name: str, good: str, bad: str) -> str:
        return good if checks[name].passed else f"**{bad}** (`evidence/repo-checks.txt`)"

    rows = {
        1: f"{len(changed)} file(s) staged. " + result("audit", "Audit CLEAN (`evidence/repo-checks.txt`)", "Audit NOT CLEAN"),
        3: result("message", "the message audit is CLEAN", "the message audit is NOT CLEAN"),
        6: "; ".join([result("tests", f"{ran.group(1) if ran else '?'} tests pass", "the tests FAIL"),
                      result("docs", "the docs check is OK", "the docs check is NOT OK"),
                      result("syntax", f"`bash -n` passes on {len(shell)} scripts", "`bash -n` FAILS"),
                      result("shellcheck", f"shellcheck {shellcheck_version} passes on them", "shellcheck FAILS or is not installed")]),
    }
    subject = message.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0]
    # The base as a reader knows it: a commit by its short hash, and whether it is the latest origin/main.
    commit = git("rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}", check=False).strip()
    if commit:
        on = f"`{commit[:7]}`"
        if origin:
            on += ", which is `origin/main`" if commit == origin else ", which is not `origin/main`"
    else:
        on = f"the tree `{base[:7]}`, a proposal that isn't committed yet"
    review = pack / "REVIEW.md"
    if review.exists():
        print(f"{review} is there already and was left as it is. Its checks today:")
        for number, row in rows.items():
            print(f"  {number}: {row}")
    else:
        review.write_text(skeleton(subject, on, tree[:7], stat, documents, rows), encoding="utf-8")
        print(f"wrote {review}: fill in what is marked {TO_WRITE}")
    print(f"pack: {pack} (commit.diff: {stat}; {len(documents)} document(s); evidence/repo-checks.txt)")
    if failed:
        print(f"NOT READY: {len(failed)} check(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"READY FOR REVIEW: {len(checks)} checks passed on the staged tree {tree[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
