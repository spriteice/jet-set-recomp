# Release checklist

No build made from the disc is ever published, so a Jet Set Recomp release is source only: the repository
at a tag, which players build with their own disc. A release is tagged and published only on my say-so,
and how releases are named hasn't been decided yet. Backlogs live in the shared
folder's `release-prep/`, and `known-bugs.md` at its root.

## The gate

No release ships with an open critical bug. A bug is critical when, on Windows or Linux, it stops the
game starting, freezes or crashes it, loses saves or settings, or stops a player progressing, however
rarely. I can decide a bug isn't critical, with the reason written in `known-bugs.md`, but can't ship one
that is.

## The steps

1. **Backlog closed:** each item done, or moved with my OK.
2. **Switches retired,** and nothing left on from debugging.
3. **Main ready:** latest `origin/main`, nothing unpushed from elsewhere, a clean tree.
4. **Known bugs current,** each open bug marked critical or not. A critical one stops the release here.
5. **Rules review** of everything since the last release: the audit, session links in commit messages,
   address lists, sleeps, code making up for another layer, a second fix with no review, hooks that look
   alike, regression tests, and docs that changed with their code. Fix findings now, one commit each.
6. **Docs:** the README, `docs/`, `packaging/README.txt`, the changelog, and the release text.
7. **Build from a clean checkout,** following the README's own steps, for both platforms. Run the gate
   and the two 10-minute runs against `data/baseline.json`.
8. **Test those builds** on the Ally X (Desktop and Game Mode) and the Windows PC, including a fresh setup
   and an upgrade over the last release's saves. If anything fails: fix, recheck, rebuild.
9. **Go-ahead:** I approve publishing, with every step passed and no open critical bug.
10. **Push and publish,** source only. Check that no release asset holds a built program.
11. **Check the release:** the tag is on the release commit, and the README's links work.
12. **Close out:** a source backup (`git clone --mirror`, `git bundle`, checked with `git fsck`), the
    backlog marked shipped, and the roadmap moved on.

A published tag is never moved. A broken release is fixed in the next one, and listed as a known issue
until then.
